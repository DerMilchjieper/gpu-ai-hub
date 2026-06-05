import json
import os
import subprocess
import time
from typing import Any, Dict

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

def get_gpu_data() -> Dict[str, Any]:
    try:
        # Query nvidia-smi for all relevant fields
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free,fan.speed,power.draw,power.limit",
            "--format=csv,noheader,nounits"
        ]
        output = subprocess.check_output(cmd, text=True).strip()
        parts = [p.strip() for p in output.split(",")]
        
        return {
            "name": parts[0],
            "temp": int(parts[1]),
            "util": int(parts[2]),
            "vram_util": int(parts[3]),
            "vram_total": int(parts[4]),
            "vram_used": int(parts[5]),
            "vram_free": int(parts[6]),
            "fan": int(parts[7]) if parts[7] != "[N/A]" else 0,
            "power": float(parts[8]),
            "power_limit": float(parts[9])
        }
    except Exception as e:
        return {"error": str(e)}

def get_cpu_data() -> Dict[str, Any]:
    return {
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_total": round(psutil.virtual_memory().total / (1024**3), 1),
        "ram_used": round(psutil.virtual_memory().used / (1024**3), 1),
        "ram_percent": psutil.virtual_memory().percent,
        "load": os.getloadavg()
    }

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen System</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #090d12;
      --panel: rgba(16, 22, 29, 0.94);
      --panel-strong: rgba(20, 28, 37, 0.98);
      --line: rgba(150, 171, 194, 0.22);
      --text: #eef4fb;
      --muted: #9aaabd;
      --brand: #55d6bd;
      --brand-2: #f6c36d;
      --danger: #ff7b72;
      --shadow: 0 18px 42px rgba(0, 0, 0, 0.34);
      --radius: 8px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: "Segoe UI", Inter, ui-sans-serif, sans-serif;
      background:
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(180deg, #090d12 0%, #07090d 100%);
      background-size: 32px 32px, 32px 32px, auto;
    }
    .site-menu { width: 100%; border-bottom: 1px solid var(--line); background: rgba(9, 13, 18, 0.92); backdrop-filter: blur(14px); position: sticky; top: 0; z-index: 50; }
    .site-menu-inner { width: min(1240px, calc(100% - 36px)); min-height: 58px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    .site-brand { color: var(--text); font-weight: 800; font-size: 15px; letter-spacing: 0; text-decoration: none; white-space: nowrap; }
    .site-nav { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
    .site-nav a { min-height: 36px; display: inline-flex; align-items: center; justify-content: center; padding: 0 12px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); text-decoration: none; font-size: 13px; font-weight: 700; }
    .site-nav a:hover { background: #20354a; }
    .site-nav a[data-current="1"] { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    .shell { width: min(1240px, calc(100% - 36px)); margin: 0 auto; padding: 28px 0 48px; }
    header { display: grid; grid-template-columns: 1fr; gap: 18px; align-items: stretch; margin-bottom: 18px; }
    .panel, .card { border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); box-shadow: var(--shadow); backdrop-filter: blur(14px); }
    .hero { padding: 28px; }
    .eyebrow { color: var(--brand); text-transform: uppercase; letter-spacing: 0.18em; font-size: 12px; font-weight: 800; }
    h1 { margin: 12px 0 14px; font-size: clamp(38px, 5vw, 64px); line-height: 0.95; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.6; margin: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
    .card { padding: 20px; display: grid; gap: 14px; }
    .label { color: var(--muted); font-size: 13px; font-weight: 700; text-transform: uppercase; }
    .value { font-size: 32px; font-weight: 800; }
    .bar { height: 10px; background: rgba(255,255,255,0.05); border-radius: 99px; overflow: hidden; border: 1px solid var(--line); }
    .fill { height: 100%; background: var(--brand); transition: width 0.3s ease; }
    .fill.warn { background: var(--brand-2); }
    .fill.danger { background: var(--danger); }
    .stats-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="system">
  <div class="site-menu">
    <div class="site-menu-inner">
      <a class="site-brand" data-nav="hub" href="http://192.168.2.41:8191/">Zen AI Hub</a>
            <nav class="site-nav" aria-label="Zen AI Hub Navigation">
        <a data-nav="hub" href="http://192.168.2.41:8191/">Hub</a>
        <a data-nav="gallery" href="http://192.168.2.41:8009/">Gallery</a>
        <a data-nav="audio" href="http://192.168.2.41:8010/">Audio</a>
        <a data-nav="system" href="http://192.168.2.41:8008/">System</a>
        <a data-nav="queue" href="http://192.168.2.41:11435/status">GPU Queue</a>
        <a data-nav="vision" href="http://192.168.2.41:8003/">Vision</a>
        <a data-nav="voice" href="http://192.168.2.41:8002/">Voice Pro</a>
        <a data-nav="docs" href="http://192.168.2.41:8004/">Docs</a>
        <a data-nav="video" href="http://192.168.2.41:8005/">Video Lab</a>
        <a data-nav="coder" href="http://192.168.2.41:8006/">Coder</a>
        <a data-nav="auto" href="http://192.168.2.41:8007/">Automator</a>
        <a data-nav="n8n" href="http://192.168.2.41:5678/" target="_blank" rel="noreferrer">n8n</a>
        <a data-nav="whisper" href="http://192.168.2.41:8000/">Whisper</a>
        <a data-nav="workspace" href="http://192.168.2.41:8001/?workspace=1">Workspace</a>
        <a data-nav="comfy" href="http://192.168.2.41:8188/" target="_blank" rel="noreferrer">ComfyUI</a>
      </nav>
    </div>
  </div>
  <script>
    (() => {
      const host = window.location.hostname || "192.168.2.41";
      const urls = { hub: `http://${host}:8191/`, queue: `http://${host}:11435/status`, gallery: `http://${host}:8009/`, system: `http://${host}:8008/`, audio: `http://${host}:8010/`, vision: `http://${host}:8003/`, voice: `http://${host}:8002/`, docs: `http://${host}:8004/`, video: `http://${host}:8005/`, coder: `http://${host}:8006/`, auto: `http://${host}:8007/`, n8n: `http://${host}:5678/`, whisper: `http://${host}:8000/`, workspace: `http://${host}:8001/?workspace=1`, comfy: `http://${host}:8188/` };
      document.querySelectorAll("[data-nav]").forEach((link) => { const key = link.dataset.nav; if (urls[key]) link.href = urls[key]; });
      const active = document.body.dataset.page;
      document.querySelectorAll(`[data-nav="${active}"]`).forEach((link) => { link.dataset.current = "1"; });
    })();
  </script>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen System</div>
        <h1>Hardware Monitoring.</h1>
        <p>Live-Statistiken fuer die RTX 3090 und den Threadripper. Behalte Temperatur, VRAM und Last immer im Blick.</p>
      </section>
    </header>
    <section class="grid">
      <div class="card">
        <div class="label">NVIDIA GeForce RTX 3090</div>
        <div class="value" id="gpuName">-</div>
        <div class="stats-row">
            <div><div class="label">Last</div><div class="value" id="gpuUtil">-</div></div>
            <div><div class="label">Temp</div><div class="value" id="gpuTemp">-</div></div>
        </div>
        <div class="bar"><div id="gpuBar" class="fill" style="width: 0%"></div></div>
      </div>

      <div class="card">
        <div class="label">VRAM Belegung (24 GB)</div>
        <div class="value" id="vramUsed">-</div>
        <div class="bar"><div id="vramBar" class="fill" style="width: 0%"></div></div>
        <div class="label" id="vramFree">Frei: -</div>
      </div>

      <div class="card">
        <div class="label">Threadripper CPU</div>
        <div class="value" id="cpuUsage">-</div>
        <div class="bar"><div id="cpuBar" class="fill" style="width: 0%"></div></div>
        <div class="label" id="cpuCount">Kerne: -</div>
      </div>

      <div class="card">
        <div class="label">System RAM</div>
        <div class="value" id="ramUsage">-</div>
        <div class="bar"><div id="ramBar" class="fill" style="width: 0%"></div></div>
        <div class="label" id="ramTotal">Total: -</div>
      </div>

      <div class="card">
        <div class="label">Power & Cooling</div>
        <div class="stats-row">
            <div><div class="label">Power</div><div class="value" id="gpuPower">-</div></div>
            <div><div class="label">Fan Speed</div><div class="value" id="gpuFan">-</div></div>
        </div>
      </div>
    </section>
  </main>
  <script>
    async function update() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            const gpu = data.gpu;
            const cpu = data.cpu;

            document.getElementById('gpuName').textContent = gpu.name;
            document.getElementById('gpuUtil').textContent = gpu.util + '%';
            document.getElementById('gpuTemp').textContent = gpu.temp + '°C';
            const gpuBar = document.getElementById('gpuBar');
            gpuBar.style.width = gpu.util + '%';
            gpuBar.className = 'fill ' + (gpu.temp > 75 ? 'danger' : (gpu.temp > 65 ? 'warn' : ''));

            document.getElementById('vramUsed').textContent = gpu.vram_used + ' MiB';
            document.getElementById('vramFree').textContent = 'Frei: ' + gpu.vram_free + ' MiB';
            document.getElementById('vramBar').style.width = (gpu.vram_used / gpu.vram_total * 100) + '%';

            document.getElementById('cpuUsage').textContent = cpu.cpu_usage + '%';
            document.getElementById('cpuBar').style.width = cpu.cpu_usage + '%';
            document.getElementById('cpuCount').textContent = cpu.cpu_count + ' Threads';

            document.getElementById('ramUsage').textContent = cpu.ram_used + ' GB';
            document.getElementById('ramTotal').textContent = 'Total: ' + cpu.ram_total + ' GB';
            document.getElementById('ramBar').style.width = cpu.ram_percent + '%';

            document.getElementById('gpuPower').textContent = gpu.power + 'W';
            document.getElementById('gpuFan').textContent = gpu.fan + '%';

        } catch (e) { console.error(e); }
    }
    setInterval(update, 2000);
    update();
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.get('/api/stats')
def stats():
    return {
        "gpu": get_gpu_data(),
        "cpu": get_cpu_data()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
