import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import requests
import torch
from fastapi import Body, FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from scipy.io.wavfile import write

app = FastAPI()

# GPU Orchestrator config
ORCHESTRATOR_URL = "http://127.0.0.1:11435/audio/generate"
INTERNAL_PORT = 8010

AUDIO_ROOT = Path("/home/wizzard/ai/audio_gen")
OUTPUT_DIR = AUDIO_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Global model state
MODEL = None
PROCESSOR = None

def get_model():
    global MODEL, PROCESSOR
    if MODEL is None:
        from transformers import MusicgenForConditionalGeneration, AutoProcessor
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading MusicGen model on {device}...")
        PROCESSOR = AutoProcessor.from_pretrained("facebook/musicgen-small")
        MODEL = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small").to(device)
    return MODEL, PROCESSOR

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Audio</title>
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
    header { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 0.62fr); gap: 18px; align-items: stretch; margin-bottom: 18px; }
    .panel, .card { border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); box-shadow: var(--shadow); backdrop-filter: blur(14px); }
    .hero { padding: 28px; }
    .side { padding: 18px; display: grid; gap: 12px; align-content: center; background: linear-gradient(135deg, rgba(85,214,189,0.09), rgba(246,195,109,0.05)), var(--panel); }
    .eyebrow { color: var(--brand); text-transform: uppercase; letter-spacing: 0.18em; font-size: 12px; font-weight: 800; }
    h1 { margin: 12px 0 14px; font-size: clamp(38px, 5vw, 64px); line-height: 0.95; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.6; margin: 0; }
    .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(350px, 0.7fr); gap: 14px; }
    .card { padding: 18px; display: grid; gap: 14px; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"], input[type="range"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    .status { color: var(--muted); min-height: 24px; }
    audio { width: 100%; margin-top: 10px; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="audio">
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
        <div class="eyebrow">Zen Audio</div>
        <h1>Music Generation.</h1>
        <p>Erzeuge Musik aus Text-Prompts mit Meta's MusicGen. Lokal auf deiner GPU, sicher verwaltet durch die GPU-Queue.</p>
      </section>
    </header>
    <section class="grid">
      <div class="card">
        <label>Musik Prompt<textarea id="promptInput" rows="4">Cyberpunk synthwave track with heavy bass and melodic neon lead, fast tempo.</textarea></label>
        <label>Dauer (Sekunden) <span id="durValue">10</span><input type="range" id="duration" min="5" max="30" step="1" value="10"></label>
        <div class="actions">
          <button class="primary" id="genBtn">Musik erzeugen</button>
        </div>
        <div class="status" id="statusLine">Bereit.</div>
      </div>
      
      <div class="card controls">
        <label>Ergebnis</label>
        <div class="result" id="resultBox">
            <audio id="audioPlayer" controls class="hidden"></audio>
            <span class="badge hidden" id="timeBadge">-</span>
            <div id="downloadContainer" class="hidden" style="margin-top:10px;">
                <a class="button-link primary" id="downloadLink" href="#" download>Herunterladen</a>
            </div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        promptInput: document.getElementById("promptInput"),
        duration: document.getElementById("duration"),
        durValue: document.getElementById("durValue"),
        genBtn: document.getElementById("genBtn"),
        statusLine: document.getElementById("statusLine"),
        audioPlayer: document.getElementById("audioPlayer"),
        timeBadge: document.getElementById("timeBadge"),
        downloadContainer: document.getElementById("downloadContainer"),
        downloadLink: document.getElementById("downloadLink")
    };

    elements.duration.oninput = () => { elements.durValue.textContent = elements.duration.value; };

    elements.genBtn.onclick = async () => {
        const prompt = elements.promptInput.value.trim();
        const duration = parseInt(elements.duration.value);
        
        elements.genBtn.disabled = true;
        elements.statusLine.textContent = 'Warte auf GPU Orchestrator...';
        elements.timeBadge.classList.add('hidden');
        
        const startTime = Date.now();
        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ prompt, duration })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            
            elements.audioPlayer.src = `/api/download/${data.filename}`;
            elements.audioPlayer.classList.remove('hidden');
            elements.downloadLink.href = `/api/download/${data.filename}`;
            elements.downloadContainer.classList.remove('hidden');
            
            const duration_s = ((Date.now() - startTime) / 1000).toFixed(1);
            elements.statusLine.textContent = `Fertig in ${duration_s}s`;
            elements.timeBadge.textContent = `${duration_s}s`;
            elements.timeBadge.classList.remove('hidden');
            
        } catch (e) {
            elements.statusLine.textContent = `Fehler: ${e.message}`;
        } finally {
            elements.genBtn.disabled = false;
        }
    };
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.post('/api/generate')
def generate(payload: dict = Body(...)):
    # External API: forwards to Orchestrator
    try:
        response = requests.post(ORCHESTRATOR_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orchestrator Error: {str(e)}")

@app.post('/api/internal/generate')
def internal_generate(payload: dict = Body(...)):
    # Internal API: Called by Orchestrator
    prompt = payload.get('prompt', 'Happy music')
    duration = payload.get('duration', 10)
    
    model, processor = get_model()
    
    inputs = processor(
        text=[prompt],
        padding=True,
        return_tensors="pt",
    ).to(model.device)
    
    # Approx 50 tokens per second of audio
    max_tokens = int(duration * 50)
    
    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_tokens)
    
    sampling_rate = model.config.audio_encoder.sampling_rate
    filename = f"{uuid.uuid4().hex[:8]}.wav"
    output_path = OUTPUT_DIR / filename
    
    # Save as WAV
    data = audio_values[0, 0].cpu().numpy()
    write(str(output_path), sampling_rate, data)
    
    return {"status": "ok", "filename": filename}

@app.post('/api/offload')
def offload():
    global MODEL, PROCESSOR
    if MODEL is not None:
        print("Offloading MusicGen from GPU...")
        MODEL = None
        PROCESSOR = None
        torch.cuda.empty_cache()
    return {"status": "ok"}

@app.get('/api/download/{filename}')
def download_file(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(path)

if __name__ == "__main__":
    import uvicorn
    # Important: Run on Port 8011 for internal worker, Port 8010 for UI is handled by Uvicorn in service
    uvicorn.run(app, host="0.0.0.0", port=8011)
