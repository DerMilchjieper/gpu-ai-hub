#!/usr/bin/env python3
"""GPU-only AI request orchestrator.

Routes local AI HTTP requests through a single FIFO queue and waits for GPU
headroom before forwarding them. This intentionally does not provide a CPU
fallback. If the GPU is unavailable, jobs wait until their timeout and fail.
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

import requests

HOST = os.getenv("GPU_ORCH_HOST", "0.0.0.0")
PORT = int(os.getenv("GPU_ORCH_PORT", "11435"))
GPU_INDEX = os.getenv("GPU_ORCH_GPU_INDEX", "0")
POLL_SECONDS = float(os.getenv("GPU_ORCH_POLL_SECONDS", "2"))
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("GPU_ORCH_JOB_TIMEOUT_SECONDS", "7200"))
STRICT_OLLAMA_GPU = os.getenv("GPU_ORCH_STRICT_OLLAMA_GPU", "1").lower() not in {"0", "false", "no"}
AUTO_OFFLOAD = os.getenv("GPU_ORCH_AUTO_OFFLOAD", "1").lower() not in {"0", "false", "no"}
AUTO_OFFLOAD_DELAY_SECONDS = float(os.getenv("GPU_ORCH_AUTO_OFFLOAD_DELAY_SECONDS", "0"))

TARGETS = {
    "ollama": os.getenv("GPU_ORCH_OLLAMA", "http://127.0.0.1:11434"),
    "whisper": os.getenv("GPU_ORCH_WHISPER", "http://127.0.0.1:8001"),
    "comfy": os.getenv("GPU_ORCH_COMFY", "http://127.0.0.1:8188"),
}

MIN_FREE_MIB = {
    "ollama": int(os.getenv("GPU_ORCH_OLLAMA_MIN_FREE_MIB", "2048")),
    "whisper": int(os.getenv("GPU_ORCH_WHISPER_MIN_FREE_MIB", "2500")),
    "comfy": int(os.getenv("GPU_ORCH_COMFY_MIN_FREE_MIB", "8192")),
}

STATE_LOCK = threading.Lock()
CURRENT_JOB: dict[str, Any] | None = None
COMPLETED: list[dict[str, Any]] = []
WORK_QUEUE: queue.Queue["Job"] = queue.Queue()


@dataclass
class ResponsePayload:
    status_code: int = 502
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


@dataclass
class Job:
    id: str
    created_at: float
    method: str
    service: str
    path: str
    query: str
    headers: dict[str, str]
    body: bytes
    min_free_mib: int
    timeout_seconds: int
    done: threading.Event = field(default_factory=threading.Event)
    response: ResponsePayload | None = None
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None


def gpu_snapshot() -> dict[str, Any]:
    cmd = [
        "nvidia-smi",
        f"--id={GPU_INDEX}",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=10).strip()
        index, name, total, used, free, util = [part.strip() for part in output.split(",")]
        return {
            "ok": True,
            "index": int(index),
            "name": name,
            "memory_total_mib": int(total),
            "memory_used_mib": int(used),
            "memory_free_mib": int(free),
            "utilization_gpu_pct": int(util),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def gpu_processes() -> list[dict[str, Any]]:
    cmd = [
        "nvidia-smi",
        "--query-compute-apps=pid,process_name,used_memory",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=10).strip()
    except Exception:
        return []
    processes: list[dict[str, Any]] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        pid, process_name, used_memory = parts
        try:
            used_memory_mib = int(used_memory)
        except ValueError:
            used_memory_mib = 0
        processes.append({
            "pid": int(pid),
            "process_name": process_name,
            "used_memory_mib": used_memory_mib,
            "tool": classify_process(process_name),
        })
    return processes


def classify_process(process_name: str) -> str:
    lower = process_name.lower()
    if "ollama" in lower:
        return "ollama"
    if "whisper" in lower or "uvicorn" in lower:
        return "whisper"
    if "comfyui" in lower or "comfy" in lower:
        return "comfy"
    if "xorg" in lower:
        return "desktop"
    return "other"


def parse_ollama_ps() -> list[dict[str, Any]]:
    output = ollama_processors()
    lines = [line for line in output.splitlines() if line.strip()]
    models: list[dict[str, Any]] = []
    for line in lines[1:]:
        columns = re.split(r"\s{2,}", line.strip())
        if len(columns) < 6:
            continue
        models.append({
            "name": columns[0],
            "id": columns[1],
            "size": columns[2],
            "processor": columns[3],
            "context": columns[4],
            "until": columns[5],
            "raw": line,
        })
    return models


def whisper_status() -> dict[str, Any]:
    try:
        response = requests.get(TARGETS["whisper"].rstrip("/") + "/api/status", timeout=5)
        return response.json()
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def comfy_status() -> dict[str, Any]:
    try:
        response = requests.get(TARGETS["comfy"].rstrip("/") + "/system_stats", timeout=5)
        data = response.json()
        return {
            "status": "ok",
            "devices": [
                {
                    "name": device.get("name"),
                    "type": device.get("type"),
                    "index": device.get("index"),
                    "vram_total_mib": round((device.get("vram_total") or 0) / 1024 / 1024),
                    "vram_free_mib": round((device.get("vram_free") or 0) / 1024 / 1024),
                    "torch_vram_total_mib": round((device.get("torch_vram_total") or 0) / 1024 / 1024),
                    "torch_vram_free_mib": round((device.get("torch_vram_free") or 0) / 1024 / 1024),
                }
                for device in data.get("devices", [])
            ],
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def tool_usage() -> dict[str, Any]:
    processes = gpu_processes()
    by_tool: dict[str, dict[str, Any]] = {}
    for proc in processes:
        bucket = by_tool.setdefault(proc["tool"], {"used_memory_mib": 0, "processes": []})
        bucket["used_memory_mib"] += proc["used_memory_mib"]
        bucket["processes"].append(proc)
    return {
        "processes": processes,
        "by_tool": by_tool,
        "models": {
            "ollama": parse_ollama_ps(),
            "whisper": whisper_status(),
            "comfy": comfy_status(),
        },
    }


def wait_for_gpu(min_free_mib: int, deadline: float) -> None:
    while time.time() < deadline:
        snap = gpu_snapshot()
        if snap.get("ok") and snap.get("memory_free_mib", 0) >= min_free_mib:
            return
        time.sleep(POLL_SECONDS)
    snap = gpu_snapshot()
    raise TimeoutError(f"GPU queue timeout waiting for {min_free_mib} MiB free VRAM; last_snapshot={snap}")


def ollama_processors() -> str:
    try:
        return subprocess.check_output(["ollama", "ps"], text=True, stderr=subprocess.STDOUT, timeout=15)
    except Exception as exc:
        return f"ollama ps failed: {exc}"


def loaded_ollama_models() -> list[str]:
    output = ollama_processors()
    lines = [line for line in output.splitlines() if line.strip()]
    models: list[str] = []
    for line in lines[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def offload_ollama() -> None:
    for model_name in loaded_ollama_models():
        subprocess.run(["ollama", "stop", model_name], capture_output=True, text=True, timeout=30)


def offload_whisper() -> None:
    try:
        requests.post(TARGETS["whisper"].rstrip("/") + "/api/deactivate", timeout=20)
    except Exception:
        pass


def offload_comfy() -> None:
    try:
        requests.post(
            TARGETS["comfy"].rstrip("/") + "/free",
            json={"unload_models": True, "free_memory": True},
            timeout=20,
        )
    except Exception:
        pass


def release_other_gpu_users(service: str) -> None:
    if service != "ollama":
        offload_ollama()
    if service != "whisper":
        offload_whisper()
    if service != "comfy":
        offload_comfy()


def offload_all() -> None:
    offload_ollama()
    offload_whisper()
    offload_comfy()


def offload_after_job(service: str) -> None:
    if not AUTO_OFFLOAD:
        return
    if AUTO_OFFLOAD_DELAY_SECONDS > 0:
        time.sleep(AUTO_OFFLOAD_DELAY_SECONDS)
    if service == "ollama":
        offload_ollama()
    elif service == "whisper":
        offload_whisper()
    elif service == "comfy":
        offload_comfy()


def assert_no_ollama_cpu_offload() -> None:
    if not STRICT_OLLAMA_GPU:
        return
    output = ollama_processors()
    lines = [line for line in output.splitlines() if line.strip()]
    model_lines = lines[1:] if len(lines) > 1 else []
    offenders = [line for line in model_lines if "100% GPU" not in line]
    if offenders:
        raise RuntimeError("Ollama CPU/offload detected after request; refusing result. ollama ps:\n" + output)


def classify(path: str) -> tuple[str | None, str]:
    if path.startswith("/ollama/"):
        return "ollama", path.removeprefix("/ollama") or "/"
    if path in {"/api/generate", "/api/chat", "/api/embeddings", "/api/embed", "/api/tags", "/api/show", "/api/ps"}:
        return "ollama", path
    if path.startswith("/whisper/"):
        return "whisper", path.removeprefix("/whisper") or "/"
    if path.startswith("/comfy/"):
        return "comfy", path.removeprefix("/comfy") or "/"
    return None, path


def filtered_headers(headers: dict[str, str]) -> dict[str, str]:
    blocked = {"host", "connection", "content-length", "accept-encoding"}
    return {key: value for key, value in headers.items() if key.lower() not in blocked}


def forward(job: Job) -> ResponsePayload:
    target = TARGETS[job.service].rstrip("/") + job.path
    if job.query:
        target += "?" + job.query
    response = requests.request(
        job.method,
        target,
        headers=filtered_headers(job.headers),
        data=job.body,
        timeout=job.timeout_seconds,
    )
    if job.service == "ollama":
        assert_no_ollama_cpu_offload()
    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"transfer-encoding", "connection", "content-encoding", "content-length"}
    }
    headers["X-GPU-Orchestrator-Job"] = job.id
    headers["X-GPU-Orchestrator-Service"] = job.service
    return ResponsePayload(response.status_code, headers, response.content)


def complete_record(job: Job, status: str) -> dict[str, Any]:
    return {
        "id": job.id,
        "service": job.service,
        "path": job.path,
        "status": status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "wait_sec": round((job.started_at or time.time()) - job.created_at, 3),
        "run_sec": round((job.finished_at or time.time()) - (job.started_at or time.time()), 3) if job.started_at else None,
        "error": job.error,
    }


def status_payload() -> dict[str, Any]:
    with STATE_LOCK:
        return {
            "status": "ok",
            "gpu": gpu_snapshot(),
            "usage": tool_usage(),
            "queue_depth": WORK_QUEUE.qsize(),
            "current_job": CURRENT_JOB,
            "completed_recent": COMPLETED[:10],
            "targets": TARGETS,
            "min_free_mib": MIN_FREE_MIB,
            "strict_ollama_gpu": STRICT_OLLAMA_GPU,
            "auto_offload": AUTO_OFFLOAD,
            "auto_offload_delay_seconds": AUTO_OFFLOAD_DELAY_SECONDS,
        }


DASHBOARD_HTML = r"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GPU Orchestrator</title>
  <style>
    :root { color-scheme: dark; --bg:#081018; --panel:#101a26; --line:#26384a; --text:#eaf2ff; --muted:#9db0c4; --ok:#5ee0b7; --warn:#ffca75; --bad:#ff7b7b; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; font-family:Inter,Segoe UI,sans-serif; color:var(--text); background:linear-gradient(180deg,#081018,#05080c); }
    main { width:min(1180px, calc(100vw - 32px)); margin:0 auto; padding:28px 0 42px; }
    header { display:flex; justify-content:space-between; gap:20px; align-items:flex-start; margin-bottom:18px; }
    h1 { margin:0; font-size:clamp(34px,5vw,58px); letter-spacing:-0.03em; }
    .sub { color:var(--muted); margin:8px 0 0; max-width:70ch; line-height:1.5; }
    .grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:18px 0; }
    .card, table { border:1px solid var(--line); background:rgba(16,26,38,.92); border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,.28); }
    .card { padding:16px; min-height:110px; }
    .label { color:var(--muted); font-size:13px; }
    .value { font-size:28px; font-weight:800; margin-top:8px; overflow-wrap:anywhere; }
    .ok { color:var(--ok); } .warn { color:var(--warn); } .bad { color:var(--bad); }
    .bar { height:14px; border-radius:999px; background:#1c2b3b; overflow:hidden; margin-top:12px; border:1px solid rgba(255,255,255,.08); }
    .fill { height:100%; width:0%; background:linear-gradient(90deg,var(--ok),var(--warn)); transition:width .2s ease; }
    section { margin-top:18px; }
    h2 { font-size:18px; margin:0 0 10px; }
    table { width:100%; border-collapse:collapse; overflow:hidden; }
    th,td { padding:11px 12px; text-align:left; border-bottom:1px solid rgba(255,255,255,.07); font-size:14px; vertical-align:top; }
    th { color:var(--muted); font-weight:700; }
    tr:last-child td { border-bottom:0; }
    code { color:#bde7ff; }
    .pill { display:inline-flex; padding:6px 10px; border-radius:999px; background:#18283a; border:1px solid var(--line); color:var(--muted); font-size:13px; }
    .actions { display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; }
    a, button { color:var(--text); background:#17283a; border:1px solid var(--line); border-radius:10px; padding:10px 12px; text-decoration:none; font:inherit; cursor:pointer; }
    @media (max-width:900px) { header { flex-direction:column; } .grid { grid-template-columns:1fr 1fr; } .actions { justify-content:flex-start; } }
    @media (max-width:560px) { .grid { grid-template-columns:1fr; } }
  

    /* Zen AI Hub unified control theme. */
    :root {
      color-scheme: dark;
      --bg:#090d12;
      --panel:rgba(16,22,29,.94);
      --panel-strong:rgba(20,28,37,.98);
      --line:rgba(150,171,194,.22);
      --text:#eef4fb;
      --muted:#9aaabd;
      --ok:#55d6bd;
      --warn:#f6c36d;
      --bad:#ff7b72;
      --shadow:0 18px 42px rgba(0,0,0,.34);
      --radius:8px;
    }
    body {
      font-family:"Segoe UI", Inter, ui-sans-serif, sans-serif;
      background:
        linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.02) 1px, transparent 1px),
        linear-gradient(180deg,#090d12 0%,#07090d 100%);
      background-size:32px 32px,32px 32px,auto;
    }
    main { width:min(1240px, calc(100vw - 36px)); padding:28px 0 48px; }
    h1 { font-size:clamp(38px,5vw,72px); letter-spacing:0; line-height:.95; }
    .sub { color:var(--muted); font-size:17px; }
    .grid { grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; }
    .card, table {
      border-color:var(--line);
      background:var(--panel);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
    }
    .card { min-height:112px; padding:16px; }
    .value { font-size:26px; }
    .bar { background:rgba(255,255,255,.055); border-color:var(--line); border-radius:8px; }
    .fill { background:linear-gradient(90deg,var(--ok),var(--warn)); }
    .pill, a, button {
      border-color:var(--line);
      border-radius:8px;
      background:rgba(255,255,255,.055);
      color:var(--text);
    }
    a:hover, button:hover { background:#20354a; }
    th,td { border-bottom-color:rgba(150,171,194,.16); }
    code { color:#c4d1df; }


    /* Shared top navigation across Zen AI Hub tools. */
    .site-menu {
      width: 100%;
      border-bottom: 1px solid var(--line);
      background: rgba(9, 13, 18, 0.92);
      backdrop-filter: blur(14px);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .site-menu-inner {
      width: min(1240px, calc(100% - 36px));
      min-height: 58px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .site-brand {
      color: var(--text, var(--ink));
      font-weight: 800;
      font-size: 15px;
      letter-spacing: 0;
      text-decoration: none;
      white-space: nowrap;
    }
    .site-nav {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }
    .site-nav a {
      min-height: 36px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,0.055);
      color: var(--text, var(--ink));
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
    }
    .site-nav a:hover { background: #20354a; }
    .site-nav a[data-current="1"] {
      background: #1f8f7a;
      color: #06100e;
      border-color: rgba(85,214,189,0.55);
    }
    @media (max-width: 760px) {
      .site-menu-inner { align-items: stretch; flex-direction: column; padding: 10px 0; }
      .site-nav { justify-content: flex-start; }
      .site-nav a { flex: 1 1 auto; }
    }
</style>
</head>
<body data-page="queue">
  <div class="site-menu">
    <div class="site-menu-inner">
      <a class="site-brand" data-nav="hub" href="http://192.168.2.41:8191/">Zen AI Hub</a>
      <nav class="site-nav" aria-label="Zen AI Hub Navigation">
        <a data-nav="hub" href="http://192.168.2.41:8191/">Hub</a>
        <a data-nav="queue" href="http://192.168.2.41:11435/status">GPU Queue</a>
        <a data-nav="whisper" href="http://192.168.2.41:8000/">Whisper</a>
        <a data-nav="workspace" href="http://192.168.2.41:8001/?workspace=1">Workspace</a>
        <a data-nav="comfy" href="http://192.168.2.41:8188/" target="_blank" rel="noreferrer">ComfyUI</a>
      </nav>
    </div>
  </div>
  <script>
    (() => {
      const host = window.location.hostname || "192.168.2.41";
      const urls = {
        hub: `http://${host}:8191/`,
        queue: `http://${host}:11435/status`,
        whisper: `http://${host}:8000/`,
        workspace: `http://${host}:8001/?workspace=1`,
        comfy: `http://${host}:8188/`,
      };
      document.querySelectorAll("[data-nav]").forEach((link) => {
        const key = link.dataset.nav;
        if (urls[key]) link.href = urls[key];
      });
      const active = document.body.dataset.page;
      if (active) {
        document.querySelectorAll(`[data-nav="${active}"]`).forEach((link) => {
          link.dataset.current = "1";
        });
      }
    })();
  </script>
<main>
  <header>
    <div>
      <h1>GPU Orchestrator</h1>
      <p class="sub">Live-Status fuer die lokale GPU-Queue. KI-Jobs laufen FIFO und sollen warten statt auf CPU auszuweichen.</p>
    </div>
    <div class="actions">
      <a id="hubLink" href="http://192.168.2.41:8191/">KI Hub</a>
      <a href="/api/status">JSON</a>
      <button id="offloadComfyBtn">ComfyUI entladen</button>
      <button id="offloadOllamaBtn">Ollama entladen</button>
      <button id="offloadWhisperBtn">Whisper entladen</button>
      <button id="offloadBtn">Alles entladen</button>
      <button id="refreshBtn">Aktualisieren</button>
    </div>
  </header>

  <div class="grid">
    <div class="card"><div class="label">GPU</div><div class="value" id="gpuName">-</div><div class="label" id="driverState"></div></div>
    <div class="card"><div class="label">VRAM frei</div><div class="value" id="vramFree">-</div><div class="bar"><div class="fill" id="vramFill"></div></div></div>
    <div class="card"><div class="label">GPU Last</div><div class="value" id="gpuUtil">-</div><div class="bar"><div class="fill" id="utilFill"></div></div></div>
    <div class="card"><div class="label">Queue</div><div class="value" id="queueDepth">-</div><div class="label" id="currentJob">kein aktiver Job</div></div>
    <div class="card"><div class="label">Auto-Offload</div><div class="value" id="autoOffload">-</div><div class="label" id="offloadDelay">nach jedem Job</div></div>
  </div>

  <section>
    <h2>GPU-Belegung nach Tool</h2>
    <table><thead><tr><th>Tool</th><th>VRAM</th><th>Prozesse</th></tr></thead><tbody id="toolUsage"></tbody></table>
  </section>

  <section>
    <h2>Geladene Modelle</h2>
    <table><thead><tr><th>Tool</th><th>Modell</th><th>Device/Processor</th><th>Details</th></tr></thead><tbody id="models"></tbody></table>
  </section>

  <section>
    <h2>Routen</h2>
    <table><tbody id="routes"></tbody></table>
  </section>

  <section>
    <h2>Letzte Jobs</h2>
    <table><thead><tr><th>Status</th><th>Service</th><th>Pfad</th><th>Warten</th><th>Laufzeit</th><th>Fehler</th></tr></thead><tbody id="jobs"></tbody></table>
  </section>
</main>
<script>
  const fmt = new Intl.NumberFormat('de-DE');
  const hubLink = document.getElementById('hubLink');
  if (hubLink) hubLink.href = `http://${window.location.hostname || '192.168.2.41'}:8191/`;
  function setText(id, value) { document.getElementById(id).textContent = value; }
  function row(cells) { return `<tr>${cells.map((c) => `<td>${c}</td>`).join('')}</tr>`; }
  async function refresh() {
    const response = await fetch('/api/status');
    const data = await response.json();
    const gpu = data.gpu || {};
    const used = gpu.memory_used_mib || 0;
    const total = gpu.memory_total_mib || 0;
    const free = gpu.memory_free_mib || 0;
    const usedPct = total ? Math.round(used / total * 100) : 0;
    setText('gpuName', gpu.ok ? gpu.name : 'GPU Fehler');
    document.getElementById('gpuName').className = `value ${gpu.ok ? 'ok' : 'bad'}`;
    setText('driverState', gpu.ok ? `Index ${gpu.index}, ${fmt.format(total)} MiB total` : (gpu.error || 'nvidia-smi nicht verfuegbar'));
    setText('vramFree', total ? `${fmt.format(free)} MiB` : '-');
    document.getElementById('vramFill').style.width = `${usedPct}%`;
    setText('gpuUtil', gpu.ok ? `${gpu.utilization_gpu_pct}%` : '-');
    document.getElementById('utilFill').style.width = `${gpu.utilization_gpu_pct || 0}%`;
    setText('queueDepth', data.queue_depth ?? 0);
    setText('currentJob', data.current_job ? `${data.current_job.service} ${data.current_job.status}` : 'kein aktiver Job');
    setText('autoOffload', data.auto_offload ? 'AN' : 'AUS');
    document.getElementById('autoOffload').className = `value ${data.auto_offload ? 'ok' : 'warn'}`;
    setText('offloadDelay', data.auto_offload ? `Delay ${data.auto_offload_delay_seconds || 0}s` : 'Modelle bleiben geladen');
    const usage = data.usage || {};
    const byTool = usage.by_tool || {};
    document.getElementById('toolUsage').innerHTML = Object.keys(byTool).length
      ? Object.entries(byTool).sort((a, b) => (b[1].used_memory_mib || 0) - (a[1].used_memory_mib || 0)).map(([tool, info]) => row([
          `<span class="pill">${tool}</span>`,
          `${fmt.format(info.used_memory_mib || 0)} MiB`,
          (info.processes || []).map((proc) => `${proc.pid}: ${proc.process_name.split('/').pop()}`).join('<br>')
        ])).join('')
      : row(['-', '0 MiB', 'Keine Compute-Prozesse']);

    const modelRows = [];
    (usage.models?.ollama || []).forEach((model) => modelRows.push(row(['ollama', `<code>${model.name}</code>`, model.processor || '-', `${model.size || ''} ${model.until || ''}`.trim()])));
    const whisper = usage.models?.whisper || {};
    if (whisper.model_loaded) {
      const runtime = whisper.model_runtime || {};
      modelRows.push(row(['whisper', `<code>${runtime.name || 'unknown'}</code>`, `${runtime.device || '-'} ${runtime.compute_type || ''}`.trim(), runtime.fallback_reason || 'geladen']));
    }
    (usage.models?.comfy?.devices || []).forEach((device) => {
      const used = (device.vram_total_mib || 0) - (device.vram_free_mib || 0);
      if (used > 256 || device.torch_vram_total_mib > 0) {
        modelRows.push(row(['comfy', `<code>${device.name || 'cuda'}</code>`, device.type || '-', `${fmt.format(Math.max(used, 0))} MiB belegt, torch ${fmt.format(device.torch_vram_total_mib || 0)} MiB`]));
      }
    });
    document.getElementById('models').innerHTML = modelRows.length ? modelRows.join('') : row(['-', 'Keine Modelle geladen', '-', '']);

    document.getElementById('routes').innerHTML = Object.entries(data.targets || {}).map(([name, url]) => row([`<span class="pill">${name}</span>`, `<code>${url}</code>`, `${data.min_free_mib?.[name] || '-'} MiB min. frei`])).join('');
    const jobs = data.completed_recent || [];
    document.getElementById('jobs').innerHTML = jobs.length ? jobs.map((job) => row([job.status, job.service, `<code>${job.path}</code>`, `${job.wait_sec ?? '-'}s`, `${job.run_sec ?? '-'}s`, job.error || ''])).join('') : row(['-', '-', 'Noch keine Jobs seit Service-Start', '-', '-', '']);
  }
  async function offloadEndpoint(buttonId, endpoint) {
    const button = document.getElementById(buttonId);
    const oldText = button.textContent;
    button.disabled = true;
    button.textContent = 'Entlade...';
    try {
      const response = await fetch(endpoint, { method: 'POST' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } finally {
      button.disabled = false;
      button.textContent = oldText;
    }
  }
  document.getElementById('refreshBtn').addEventListener('click', refresh);
  document.getElementById('offloadBtn').addEventListener('click', () => offloadEndpoint('offloadBtn', '/api/offload'));
  document.getElementById('offloadComfyBtn').addEventListener('click', () => offloadEndpoint('offloadComfyBtn', '/api/offload/comfy'));
  document.getElementById('offloadOllamaBtn').addEventListener('click', () => offloadEndpoint('offloadOllamaBtn', '/api/offload/ollama'));
  document.getElementById('offloadWhisperBtn').addEventListener('click', () => offloadEndpoint('offloadWhisperBtn', '/api/offload/whisper'));
  refresh();
  setInterval(refresh, 3000);
</script>
</body>
</html>"""


def worker() -> None:
    global CURRENT_JOB
    while True:
        job = WORK_QUEUE.get()
        with STATE_LOCK:
            CURRENT_JOB = complete_record(job, "waiting_gpu")
        try:
            deadline = job.created_at + job.timeout_seconds
            release_other_gpu_users(job.service)
            wait_for_gpu(job.min_free_mib, deadline)
            job.started_at = time.time()
            with STATE_LOCK:
                CURRENT_JOB = complete_record(job, "running")
            job.response = forward(job)
            offload_after_job(job.service)
        except Exception as exc:
            job.error = str(exc)
            body = json.dumps({"status": "error", "job_id": job.id, "detail": job.error}, indent=2).encode()
            job.response = ResponsePayload(HTTPStatus.SERVICE_UNAVAILABLE, {"Content-Type": "application/json"}, body)
        finally:
            job.finished_at = time.time()
            with STATE_LOCK:
                COMPLETED.insert(0, complete_record(job, "error" if job.error else "done"))
                del COMPLETED[50:]
                CURRENT_JOB = None
            job.done.set()
            WORK_QUEUE.task_done()


class Handler(BaseHTTPRequestHandler):
    server_version = "GPUOrchestrator/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {self.client_address[0]} {fmt % args}", flush=True)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-GPU-Job-Timeout, X-GPU-Min-Free-MiB")

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        split = urlsplit(self.path)
        if split.path in {"/", "/status"}:
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if split.path in {"/healthz", "/api/status"}:
            self._json(200, status_payload())
            return
        service, upstream_path = classify(split.path)
        if not service:
            self._json(404, {"status": "error", "detail": "unknown route"})
            return
        try:
            target = TARGETS[service].rstrip("/") + upstream_path + (("?" + split.query) if split.query else "")
            response = requests.get(target, headers=filtered_headers(dict(self.headers)), timeout=60)
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in {"transfer-encoding", "connection", "content-encoding", "content-length"}:
                    self.send_header(key, value)
            self._cors()
            self.send_header("Content-Length", str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as exc:
            self._json(502, {"status": "error", "detail": str(exc)})

    def do_POST(self) -> None:
        split = urlsplit(self.path)
        if split.path == "/api/offload":
            try:
                offload_all()
                self._json(200, {"status": "ok", "detail": "all models offloaded", "gpu": gpu_snapshot()})
            except Exception as exc:
                self._json(503, {"status": "error", "detail": str(exc), "gpu": gpu_snapshot()})
            return
        if split.path == "/api/offload/ollama":
            try:
                offload_ollama()
                self._json(200, {"status": "ok", "detail": "ollama models offloaded", "gpu": gpu_snapshot()})
            except Exception as exc:
                self._json(503, {"status": "error", "detail": str(exc), "gpu": gpu_snapshot()})
            return
        if split.path == "/api/offload/whisper":
            try:
                offload_whisper()
                self._json(200, {"status": "ok", "detail": "whisper model offloaded", "gpu": gpu_snapshot()})
            except Exception as exc:
                self._json(503, {"status": "error", "detail": str(exc), "gpu": gpu_snapshot()})
            return
        if split.path == "/api/offload/comfy":
            try:
                offload_comfy()
                self._json(200, {"status": "ok", "detail": "comfyui models offloaded", "gpu": gpu_snapshot()})
            except Exception as exc:
                self._json(503, {"status": "error", "detail": str(exc), "gpu": gpu_snapshot()})
            return
        service, upstream_path = classify(split.path)
        if not service:
            self._json(404, {"status": "error", "detail": "unknown route"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        timeout = int(self.headers.get("X-GPU-Job-Timeout", DEFAULT_TIMEOUT_SECONDS))
        min_free = int(self.headers.get("X-GPU-Min-Free-MiB", MIN_FREE_MIB[service]))
        job = Job(
            id=str(uuid.uuid4()),
            created_at=time.time(),
            method="POST",
            service=service,
            path=upstream_path,
            query=split.query,
            headers=dict(self.headers),
            body=body,
            min_free_mib=min_free,
            timeout_seconds=timeout,
        )
        WORK_QUEUE.put(job)
        if not job.done.wait(timeout + 5):
            self._json(504, {"status": "error", "job_id": job.id, "detail": "client wait timeout"})
            return
        response = job.response or ResponsePayload(502, {"Content-Type": "application/json"}, b'{"status":"error"}')
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self._cors()
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"gpu-orchestrator listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
