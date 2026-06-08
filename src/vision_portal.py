import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

app = FastAPI()

# Point directly to the GPU Orchestrator so vision models don't crash when Comfy is running.
OLLAMA_API = "http://127.0.0.1:11435/api/generate"

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Vision</title>
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
    h1 { margin: 12px 0 14px; font-size: clamp(38px, 5vw, 72px); line-height: 0.95; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.6; margin: 0; }
    .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(350px, 0.7fr); gap: 14px; }
    .card { padding: 18px; display: grid; gap: 14px; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    textarea { min-height: 220px; resize: vertical; line-height: 1.5; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .hidden { display: none !important; }
    .status { color: var(--muted); min-height: 24px; }
    .result { display: grid; gap: 12px; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    .image-preview { max-width: 100%; border-radius: 8px; border: 1px solid var(--line); }
    label.file-picker { display: block; border: 1px dashed rgba(255,255,255,0.2); padding: 24px; text-align: center; cursor: pointer; transition: background 0.2s; }
    label.file-picker:hover { background: rgba(255,255,255,0.08); }
    label.file-picker input { display: none; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="vision">
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
        <div class="eyebrow">Zen Vision</div>
        <h1>Vision AI Analysis.</h1>
        <p>Lokale Bildanalyse mit Modellen wie Llava und Moondream via Ollama. 100% offline und ueber den GPU Orchestrator geroutet.</p>
      </section>
      <aside class="panel side">
        <label>Vision Model<select id="modelSelect">
          <option value="llava:latest">Llava (7B)</option>
          <option value="moondream:latest">Moondream (1.8B - Fast)</option>
        </select></label>
      </aside>
    </header>
    <section class="grid">
      <div class="card">
        <label class="file-picker">
          <input type="file" id="imageUpload" accept="image/png, image/jpeg, image/webp">
          Bild hochladen oder hierher ziehen (JPG/PNG/WEBP)
        </label>
        <img id="imagePreview" class="image-preview hidden" src="" alt="Preview">
        
        <label>Prompt<input type="text" id="promptInput" value="Beschreibe dieses Bild detailliert auf Deutsch."></label>
        <div class="actions">
          <button class="primary" id="analyzeBtn" disabled>Bild analysieren</button>
        </div>
        <div class="status" id="statusLine">Lade ein Bild hoch, um zu starten.</div>
      </div>
      
      <div class="card controls">
        <label>Analyse-Ergebnis<textarea id="resultOutput" readonly></textarea></label>
        <div class="result" id="resultBox">
            <span class="badge" id="timeBadge">Warte auf Bild...</span>
        </div>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        modelSelect: document.getElementById("modelSelect"),
        imageUpload: document.getElementById("imageUpload"),
        imagePreview: document.getElementById("imagePreview"),
        promptInput: document.getElementById("promptInput"),
        analyzeBtn: document.getElementById("analyzeBtn"),
        statusLine: document.getElementById("statusLine"),
        resultOutput: document.getElementById("resultOutput"),
        timeBadge: document.getElementById("timeBadge")
    };

    let currentImageBase64 = null;

    function setStatus(message) { elements.statusLine.textContent = message; }

    elements.imageUpload.onchange = () => {
        if (!elements.imageUpload.files.length) return;
        const file = elements.imageUpload.files[0];
        const reader = new FileReader();
        reader.onload = (e) => {
            elements.imagePreview.src = e.target.result;
            elements.imagePreview.classList.remove('hidden');
            currentImageBase64 = e.target.result.split(',')[1];
            elements.analyzeBtn.disabled = false;
            setStatus('Bild geladen. Bereit zur Analyse.');
            elements.timeBadge.textContent = 'Bereit';
        };
        reader.readAsDataURL(file);
    };

    async function analyze() {
        if (!currentImageBase64) return;
        const prompt = elements.promptInput.value.trim() || 'Beschreibe dieses Bild.';
        const model = elements.modelSelect.value;
        
        elements.analyzeBtn.disabled = true;
        elements.resultOutput.value = '';
        setStatus('Warte auf GPU Orchestrator...');
        elements.timeBadge.textContent = 'Analysiert...';
        
        const startTime = Date.now();
        try {
            const payload = {
                model: model,
                prompt: prompt,
                stream: false,
                images: [currentImageBase64]
            };
            
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
            
            elements.resultOutput.value = data.response || data.error || "Kein Text generiert.";
            
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            setStatus(`Fertig in ${duration}s`);
            elements.timeBadge.textContent = `${duration} Sekunden (${data.tokens_per_second || 0} t/s)`;
            
        } catch (e) { 
            setStatus(`Fehler: ${e.message}`); 
            elements.timeBadge.textContent = 'Fehler';
        } finally { 
            elements.analyzeBtn.disabled = false; 
        }
    }
    
    elements.analyzeBtn.onclick = analyze;
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.post('/api/analyze')
def analyze(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    model = payload.get('model', 'llava:latest')
    prompt = payload.get('prompt', 'Describe this image.')
    images = payload.get('images', [])
    
    if not images:
        raise HTTPException(status_code=400, detail="Kein Bild (images) im Request gefunden.")
        
    try:
        response = requests.post(
            OLLAMA_API,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "images": images
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        
        eval_duration_ns = data.get("eval_duration") or 0
        eval_count = data.get("eval_count") or 0
        tps = round(eval_count / (eval_duration_ns / 1_000_000_000), 1) if eval_duration_ns else 0.0
        
        return {
            "response": data.get("response", ""),
            "tokens_per_second": tps
        }
    except requests.exceptions.RequestException as e:
        err = str(e)
        if e.response is not None:
            err = e.response.text
        raise HTTPException(status_code=502, detail=f"Ollama/Orchestrator Error: {err}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
