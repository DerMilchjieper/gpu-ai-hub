import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import requests
from fastapi import Body, FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# GPU Orchestrator config
ORCHESTRATOR_URL = "http://127.0.0.1:11435/vibe/generate"

VIBE_ROOT = Path("/home/wizzard/ai/vibevoice")
OUTPUT_DIR = VIBE_ROOT / "outputs"
SPEAKER_DIR = VIBE_ROOT / "speakers"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SPEAKER_DIR.mkdir(parents=True, exist_ok=True)
VENV_PYTHON = str(VIBE_ROOT / "venv/bin/python")
F5_CLI = str(VIBE_ROOT / "venv/bin/f5-tts_infer-cli")

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Vibe</title>
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
    .card { padding: 18px; display: grid; gap: 14px; align-content: start; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"], input[type="range"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    .status { color: var(--muted); min-height: 24px; font-size: 13px; }
    audio { width: 100%; margin-top: 10px; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="vibe">
  <div class="site-menu">
    <div class="site-menu-inner">
      <a class="site-brand" data-nav="hub" href="http://192.168.2.41:8191/">Zen AI Hub</a>
                  <nav class="site-nav" aria-label="Zen AI Hub Navigation">
        <a data-nav="hub" href="http://192.168.2.41:8191/">Hub</a>
        <a data-nav="gallery" href="http://192.168.2.41:8009/">Gallery</a>
        <a data-nav="avatar" href="http://192.168.2.41:8013/">Avatar Live</a>
        <a data-nav="voice_live" href="http://192.168.2.41:8015/">Voice Live</a>
        <a data-nav="prompt" href="http://192.168.2.41:8012/">Prompt Expert</a>
        <a data-nav="vibe" href="http://192.168.2.41:8016/">Zen Vibe</a>
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
      const urls = { hub: `http://${host}:8191/`, gallery: `http://${host}:8009/`, audio: `http://${host}:8010/`, system: `http://${host}:8008/`, queue: `http://${host}:11435/status`, vision: `http://${host}:8003/`, vibe: `http://${host}:8016/`, voice: `http://${host}:8002/`, docs: `http://${host}:8004/`, video: `http://${host}:8005/`, coder: `http://${host}:8006/`, auto: `http://${host}:8007/`, prompt: `http://${host}:8012/`, avatar: `http://${host}:8013/`, voice_live: `http://${host}:8015/`, n8n: `http://${host}:5678/`, whisper: `http://${host}:8000/`, workspace: `http://${host}:8001/?workspace=1`, comfy: `http://${host}:8188/` };
      const nav = document.querySelector(".site-nav");
      const links = [
        {id: "hub", label: "Hub"},
        {id: "vibe", label: "Zen Vibe"},
        {id: "voice", label: "Voice Pro"},
        {id: "voice_live", label: "Voice Live"},
        {id: "avatar", label: "Avatar Live"},
        {id: "gallery", label: "Gallery"},
        {id: "system", label: "System"},
        {id: "docs", label: "Docs"},
        {id: "vision", label: "Vision"},
        {id: "video", label: "Video Lab"},
        {id: "coder", label: "Coder"},
        {id: "prompt", label: "Prompt Expert"},
        {id: "auto", label: "Automator"}
      ];
      nav.innerHTML = links.map(l => `<a data-nav="${l.id}" href="${urls[l.id]}" ${l.target ? `target="${l.target}"` : ''}>${l.label}</a>`).join('');
      document.querySelectorAll(`[data-nav="vibe"]`).forEach((link) => { link.dataset.current = "1"; });
    })();
  </script>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen Vibe (F5-TTS)</div>
        <h1>Long-Form Zero-Shot Voice Cloning.</h1>
        <p>10 Sekunden Audio-Referenz genügen. Ideal für extrem lange Texte (Podcasts, Audiobücher) ohne Halluzinationen oder Qualitätseinbußen.</p>
      </section>
      <aside class="panel side">
        <label>Engine</label>
        <div class="badge" style="width:100%; text-align:center; display:block;">F5-TTS Diffusion</div>
      </aside>
    </header>
    <section class="grid">
      <div class="card controls">
        <label>Referenz-Audio hochladen (.wav)<input type="file" id="speakerUpload" accept=".wav"></label>
        <label>Transkript der Referenz (wichtig für Perfektion)<input type="text" id="refTextInput" placeholder="Was genau wird in dem 10s-Clip gesprochen?"></label>
        <label>Geklonte Stimme (Verfügbar)<select id="speakerSelect"></select></label>
      </div>
      <div class="card">
        <label>Zu generierender Text<textarea id="promptInput" rows="10" placeholder="Füge hier deinen extrem langen Text, Podcast-Skript oder Buchkapitel ein..."></textarea></label>
        <div class="actions">
          <button class="primary" id="genBtn">Audio generieren</button>
        </div>
        <div class="status" id="statusLine">Bereit.</div>
      </div>
      
      <div class="card controls" style="grid-column: 1 / -1;">
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
        refTextInput: document.getElementById("refTextInput"),
        speakerUpload: document.getElementById("speakerUpload"),
        speakerSelect: document.getElementById("speakerSelect"),
        genBtn: document.getElementById("genBtn"),
        statusLine: document.getElementById("statusLine"),
        audioPlayer: document.getElementById("audioPlayer"),
        timeBadge: document.getElementById("timeBadge"),
        downloadContainer: document.getElementById("downloadContainer"),
        downloadLink: document.getElementById("downloadLink")
    };

    async function api(path, options = {}) { const response = await fetch(path, options); const data = await response.json(); if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`); return data; }
    
    async function loadData() {
        const speakers = await api('/api/speakers');
        elements.speakerSelect.innerHTML = speakers.speakers.map(s => `<option value="${s}">${s}</option>`).join('');
    }

    elements.speakerUpload.onchange = async () => {
        if (!elements.speakerUpload.files.length) return;
        const file = elements.speakerUpload.files[0];
        const formData = new FormData();
        formData.append('file', file);
        elements.statusLine.textContent = 'Lade Referenz hoch...';
        try {
            await api('/api/speakers/upload', { method: 'POST', body: formData });
            await loadData();
            elements.statusLine.textContent = 'Referenz hochgeladen.';
        } catch (e) { elements.statusLine.textContent = `Upload-Fehler: ${e.message}`; }
    };

    elements.genBtn.onclick = async () => {
        const prompt = elements.promptInput.value.trim();
        const speaker = elements.speakerSelect.value;
        const refText = elements.refTextInput.value.trim();
        
        if (!prompt || !speaker) return;
        
        elements.genBtn.disabled = true;
        elements.statusLine.textContent = 'Warte auf GPU Orchestrator... (Kann bei großen Modellen 20s laden)';
        elements.timeBadge.classList.add('hidden');
        
        const startTime = Date.now();
        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text: prompt, speaker: speaker, ref_text: refText })
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

    loadData();
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.get('/api/speakers')
def list_speakers() -> dict[str, Any]:
    return {'speakers': [s.name for s in sorted(SPEAKER_DIR.glob('*.wav'))]}

@app.post('/api/speakers/upload')
async def upload_speaker(file: UploadFile = File(...)):
    if not file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Nur .wav Dateien erlaubt.")
    path = SPEAKER_DIR / file.filename
    with open(path, "wb") as buffer:
        buffer.write(await file.read())
    return {"status": "ok", "filename": file.filename}

@app.post('/api/generate')
def generate(payload: dict = Body(...)):
    # External API: forwards to Orchestrator
    try:
        response = requests.post(ORCHESTRATOR_URL, json=payload, timeout=600)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orchestrator Error: {str(e)}")

@app.post('/api/internal/generate')
def internal_generate(payload: dict = Body(...)):
    # Internal API: Called by Orchestrator
    text = payload.get('text', '').strip()
    speaker = payload.get('speaker', '')
    ref_text = payload.get('ref_text', '')
    
    if not text or not speaker:
        raise HTTPException(status_code=400, detail="Text und Speaker erforderlich")
        
    speaker_path = SPEAKER_DIR / speaker
    if not speaker_path.exists():
        raise HTTPException(status_code=404, detail="Referenz nicht gefunden")
        
    filename = f"vibe_{uuid.uuid4().hex[:8]}.wav"
    output_path = OUTPUT_DIR / filename
    
    # Write temporary file for input text (F5-TTS handles long files better with -f)
    tmp_txt = VIBE_ROOT / f"tmp_{uuid.uuid4().hex[:8]}.txt"
    tmp_txt.write_text(text, encoding="utf-8")
    
    cmd = [
        VENV_PYTHON,
        F5_CLI,
        "--model", "F5-TTS",
        "--ref_audio", str(speaker_path),
        "--ref_text", ref_text,
        "--gen_file", str(tmp_txt),
        "--output_dir", str(OUTPUT_DIR),
        "--output_file", filename
    ]
    
    try:
        # Run F5-TTS
        env = os.environ.copy()
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
        
        if tmp_txt.exists():
            tmp_txt.unlink()
            
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"F5-TTS Error: {proc.stderr}")
            
        return {"status": "ok", "filename": filename}
    except subprocess.TimeoutExpired:
        if tmp_txt.exists(): tmp_txt.unlink()
        raise HTTPException(status_code=504, detail="Timeout")

@app.post('/api/internal/offload')
def offload():
    # VRAM is automatically freed since we use subprocess
    return {"status": "ok"}

@app.get('/api/download/{filename}')
def download_file(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(path)

if __name__ == "__main__":
    import uvicorn
    # UI on 8016, Worker on 8017 (started separately if needed, but we combine them for simplicity here)
    port = int(os.environ.get("VIBE_PORT", 8016))
    uvicorn.run(app, host="0.0.0.0", port=port)
