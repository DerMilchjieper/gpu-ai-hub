import json
import time
from typing import Any

import requests
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

COMFY_API_BASE = "http://127.0.0.1:8188"
GPU_ORCH_BASE = "http://127.0.0.1:11435"

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Automator</title>
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
    .card { padding: 18px; display: grid; gap: 14px; align-content: start; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    .status { color: var(--muted); min-height: 24px; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="auto">
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
        <div class="eyebrow">Zen Automator</div>
        <h1>ComfyUI Headless.</h1>
        <p>Trigger komplexe Bild- und Video-Generierungs-Workflows in ComfyUI direkt ueber die API, ohne den Graphen oeffnen zu muessen.</p>
      </section>
      <aside class="panel side">
        <label>Workflow<select id="workflowSelect">
          <option value="text_to_image_preload_clean.json">Text to Image (SDXL)</option>
          <option value="stable_fast_3d_image_to_3d.json">Image to 3D (SF3D)</option>
        </select></label>
      </aside>
    </header>
    <section class="grid">
      <div class="card">
        <label>Text Prompt<textarea id="promptInput" rows="4">A highly detailed, cinematic shot of a futuristic cyberpunk city at night with neon lights and flying cars.</textarea></label>
        <div class="actions">
          <button class="primary" id="runBtn">Workflow ausfuehren</button>
        </div>
      </div>
      
      <div class="card controls">
        <label>Status</label>
        <div class="status" id="statusLine">Bereit. Waehle einen Workflow.</div>
        <span class="badge" id="timeBadge">-</span>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        workflowSelect: document.getElementById("workflowSelect"),
        promptInput: document.getElementById("promptInput"),
        runBtn: document.getElementById("runBtn"),
        statusLine: document.getElementById("statusLine"),
        timeBadge: document.getElementById("timeBadge")
    };

    function setStatus(message) { elements.statusLine.textContent = message; }

    elements.runBtn.onclick = async () => {
        const prompt = elements.promptInput.value.trim();
        if(!prompt) return;
        
        elements.runBtn.disabled = true;
        setStatus('Trigger Workflow...');
        elements.timeBadge.textContent = 'Laeuft...';
        
        const startTime = Date.now();
        
        try {
            const res = await fetch('/api/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ workflow: elements.workflowSelect.value, prompt: prompt })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            setStatus(`Job ${data.prompt_id} gesendet! ComfyUI verarbeitet dies nun im Hintergrund.`);
            elements.timeBadge.textContent = `Gestartet in ${duration}s`;
            
        } catch (e) {
            setStatus(`Fehler: ${e.message}`);
            elements.timeBadge.textContent = 'Fehler';
        } finally {
            elements.runBtn.disabled = false;
        }
    };
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.post('/api/run')
def run_workflow(payload: dict = Body(...)):
    workflow_name = payload.get('workflow')
    user_prompt = payload.get('prompt')
    
    if not workflow_name:
        raise HTTPException(status_code=400, detail="Kein Workflow angegeben.")
        
    wf_path = f"/home/wizzard/ai/comfyui/user/default/workflows/{workflow_name}"
    if not os.path.exists(wf_path):
        wf_path = f"/home/wizzard/ai/comfyui/workflows/{workflow_name}"
        if not os.path.exists(wf_path):
            raise HTTPException(status_code=404, detail="Workflow-Datei nicht gefunden.")
            
    with open(wf_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
        
    # Super basic prompt injection (in a real scenario, you'd map specific nodes)
    # We look for a node with "text" input (usually CLIPTextEncode)
    for node_id, node_info in prompt_data.items():
        if isinstance(node_info, dict) and "inputs" in node_info:
            if "text" in node_info["inputs"] and isinstance(node_info["inputs"]["text"], str):
                node_info["inputs"]["text"] = user_prompt
                
    try:
        response = requests.post(
            f"{COMFY_API_BASE}/prompt",
            json={"prompt": prompt_data},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ComfyUI Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
