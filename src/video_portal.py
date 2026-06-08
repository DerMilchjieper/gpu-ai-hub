import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI()

VIDEO_DIR = Path("/home/wizzard/ai/video")
UPLOAD_DIR = VIDEO_DIR / "uploads"
OUTPUT_DIR = VIDEO_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Video Lab</title>
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
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .hidden { display: none !important; }
    .status { color: var(--muted); min-height: 24px; }
    .result { display: grid; gap: 12px; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    label.file-picker { display: block; border: 1px dashed rgba(255,255,255,0.2); padding: 24px; text-align: center; cursor: pointer; transition: background 0.2s; }
    label.file-picker:hover { background: rgba(255,255,255,0.08); }
    label.file-picker input { display: none; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="video">
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
        <div class="eyebrow">Zen Video Lab</div>
        <h1>Videoverarbeitung & Upscaling.</h1>
        <p>Lade Videos hoch, um sie per FFMPEG zu komprimieren, Audio zu extrahieren oder für KI-Upscaling (Real-ESRGAN) vorzubereiten. 100% lokal.</p>
      </section>
      <aside class="panel side">
        <label>Aktion<select id="actionSelect">
          <option value="compress_1080p">Komprimieren (1080p NVENC)</option>
          <option value="compress_720p">Komprimieren (720p NVENC)</option>
          <option value="extract_audio">Audio Extrahieren (MP3)</option>
          <option value="convert_mp4">Zu MP4 Konvertieren</option>
        </select></label>
      </aside>
    </header>
    <section class="grid">
      <div class="card">
        <label class="file-picker">
          <input type="file" id="videoUpload" accept="video/*">
          Video hochladen (.mp4, .mkv, .mov, .avi)
        </label>
        
        <div class="actions" style="margin-top:14px;">
          <button class="primary" id="processBtn" disabled>Video verarbeiten</button>
        </div>
        <div class="status" id="statusLine">Lade ein Video hoch.</div>
      </div>
      
      <div class="card controls">
        <label>Ergebnis</label>
        <div class="result" id="resultBox">
            <span class="badge" id="timeBadge">Warte auf Video...</span>
            <div id="downloadContainer" class="hidden" style="margin-top:10px;">
                <a class="button-link primary" id="downloadLink" href="#" download>Datei herunterladen</a>
            </div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        actionSelect: document.getElementById("actionSelect"),
        videoUpload: document.getElementById("videoUpload"),
        processBtn: document.getElementById("processBtn"),
        statusLine: document.getElementById("statusLine"),
        timeBadge: document.getElementById("timeBadge"),
        downloadContainer: document.getElementById("downloadContainer"),
        downloadLink: document.getElementById("downloadLink")
    };

    let selectedFile = null;

    function setStatus(message) { elements.statusLine.textContent = message; }

    elements.videoUpload.onchange = () => {
        if (!elements.videoUpload.files.length) return;
        selectedFile = elements.videoUpload.files[0];
        elements.processBtn.disabled = false;
        setStatus(`Video bereit: ${selectedFile.name}`);
        elements.timeBadge.textContent = 'Bereit';
        elements.downloadContainer.classList.add('hidden');
    };

    async function processVideo() {
        if (!selectedFile) return;
        const action = elements.actionSelect.value;
        
        elements.processBtn.disabled = true;
        setStatus('Lade hoch und verarbeite (das kann dauern)...');
        elements.timeBadge.textContent = 'Verarbeitet...';
        elements.downloadContainer.classList.add('hidden');
        
        const startTime = Date.now();
        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('action', action);

            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
            
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            setStatus(`Fertig in ${duration}s`);
            elements.timeBadge.textContent = 'Erfolgreich';
            
            elements.downloadLink.href = `/api/download/${data.filename}`;
            elements.downloadLink.textContent = `Download ${data.filename}`;
            elements.downloadContainer.classList.remove('hidden');
            
        } catch (e) { 
            setStatus(`Fehler: ${e.message}`); 
            elements.timeBadge.textContent = 'Fehler';
        } finally { 
            elements.processBtn.disabled = false; 
        }
    }
    
    elements.processBtn.onclick = processVideo;
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

def run_ffmpeg(input_path: Path, output_path: Path, action: str):
    cmds = {
        "compress_1080p": ["ffmpeg", "-i", str(input_path), "-vf", "scale=-2:1080", "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "26", "-c:a", "aac", "-y", str(output_path)],
        "compress_720p": ["ffmpeg", "-i", str(input_path), "-vf", "scale=-2:720", "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "28", "-c:a", "aac", "-y", str(output_path)],
        "extract_audio": ["ffmpeg", "-i", str(input_path), "-q:a", "0", "-map", "a", "-y", str(output_path)],
        "convert_mp4": ["ffmpeg", "-i", str(input_path), "-c:v", "copy", "-c:a", "aac", "-y", str(output_path)]
    }
    
    cmd = cmds.get(action)
    if not cmd:
        raise ValueError(f"Unbekannte Aktion: {action}")
        
    subprocess.run(cmd, check=True, capture_output=True)

@app.post('/api/process')
async def process_video(file: UploadFile = File(...), action: str = "convert_mp4"):
    job_id = uuid.uuid4().hex[:8]
    ext = ".mp3" if action == "extract_audio" else ".mp4"
    
    safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in file.filename)
    input_path = UPLOAD_DIR / f"{job_id}_{safe_name}"
    output_filename = f"{job_id}_out{ext}"
    output_path = OUTPUT_DIR / output_filename
    
    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        run_ffmpeg(input_path, output_path, action)
        
        # Cleanup input
        if input_path.exists():
            input_path.unlink()
            
        return {"status": "ok", "filename": output_filename}
    except subprocess.CalledProcessError as e:
        if input_path.exists(): input_path.unlink()
        if output_path.exists(): output_path.unlink()
        raise HTTPException(status_code=500, detail=f"FFMPEG Error: {e.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        if input_path.exists(): input_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/download/{filename}')
def download_file(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    return FileResponse(path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
