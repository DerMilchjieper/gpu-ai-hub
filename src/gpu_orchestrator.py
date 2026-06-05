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


def release_other_gpu_users(service: str) -> None:
    if service != "ollama":
        for model_name in loaded_ollama_models():
            subprocess.run(["ollama", "stop", model_name], capture_output=True, text=True, timeout=30)
    if service != "whisper":
        try:
            requests.post(TARGETS["whisper"].rstrip("/") + "/api/deactivate", timeout=20)
        except Exception:
            pass
    if service != "comfy":
        try:
            requests.post(
                TARGETS["comfy"].rstrip("/") + "/free",
                json={"unload_models": True, "free_memory": True},
                timeout=20,
            )
        except Exception:
            pass


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
            "queue_depth": WORK_QUEUE.qsize(),
            "current_job": CURRENT_JOB,
            "completed_recent": COMPLETED[:10],
            "targets": TARGETS,
            "min_free_mib": MIN_FREE_MIB,
            "strict_ollama_gpu": STRICT_OLLAMA_GPU,
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
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>GPU Orchestrator</h1>
      <p class="sub">Live-Status fuer die lokale GPU-Queue. KI-Jobs laufen FIFO und sollen warten statt auf CPU auszuweichen.</p>
    </div>
    <div class="actions">
      <a href="/api/status">JSON</a>
      <button id="refreshBtn">Aktualisieren</button>
    </div>
  </header>

  <div class="grid">
    <div class="card"><div class="label">GPU</div><div class="value" id="gpuName">-</div><div class="label" id="driverState"></div></div>
    <div class="card"><div class="label">VRAM frei</div><div class="value" id="vramFree">-</div><div class="bar"><div class="fill" id="vramFill"></div></div></div>
    <div class="card"><div class="label">GPU Last</div><div class="value" id="gpuUtil">-</div><div class="bar"><div class="fill" id="utilFill"></div></div></div>
    <div class="card"><div class="label">Queue</div><div class="value" id="queueDepth">-</div><div class="label" id="currentJob">kein aktiver Job</div></div>
  </div>

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
    document.getElementById('routes').innerHTML = Object.entries(data.targets || {}).map(([name, url]) => row([`<span class="pill">${name}</span>`, `<code>${url}</code>`, `${data.min_free_mib?.[name] || '-'} MiB min. frei`])).join('');
    const jobs = data.completed_recent || [];
    document.getElementById('jobs').innerHTML = jobs.length ? jobs.map((job) => row([job.status, job.service, `<code>${job.path}</code>`, `${job.wait_sec ?? '-'}s`, `${job.run_sec ?? '-'}s`, job.error || ''])).join('') : row(['-', '-', 'Noch keine Jobs seit Service-Start', '-', '-', '']);
  }
  document.getElementById('refreshBtn').addEventListener('click', refresh);
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
