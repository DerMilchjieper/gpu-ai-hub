import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
import torch

# Handle safe loading issues in newer Torch versions
_original_load = torch.load
def _patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

os.environ["COQUI_TOS_AGREED"] = "1"

app = FastAPI()

TTS_ROOT = Path('/home/wizzard/ai/tts')
PIPER_BIN = TTS_ROOT / 'bin/piper'
PIPER_LIB_DIR = TTS_ROOT / 'bin'
VOICE_DIR = TTS_ROOT / 'voices'
OUTPUT_DIR = TTS_ROOT / 'outputs'
XTTS_ROOT = TTS_ROOT / 'xtts'
SPEAKER_DIR = XTTS_ROOT / 'speakers'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SPEAKER_DIR.mkdir(parents=True, exist_ok=True)

# Cache for XTTS model
XTTS_MODEL = None

def get_xtts_model():
    global XTTS_MODEL
    if XTTS_MODEL is None:
        from TTS.api import TTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        XTTS_MODEL = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return XTTS_MODEL

VOICE_LABELS = {
    'de_DE-thorsten-medium': 'Piper: Deutsch - Thorsten medium',
    'de_DE-kerstin-low': 'Piper: Deutsch - Kerstin low',
    'de_DE-ramona-low': 'Piper: Deutsch - Ramona low',
    'en_US-lessac-medium': 'Piper: English - Lessac medium',
    'en_US-hfc_female-medium': 'Piper: English - HFC female medium',
}

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Voice Pro</title>
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
    textarea, select, input[type="range"], input[type="text"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    textarea { min-height: 220px; resize: vertical; line-height: 1.5; }
    .controls { display: grid; gap: 14px; }
    .sliders { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .hidden { display: none !important; }
    .status { color: var(--muted); min-height: 24px; }
    .result { display: grid; gap: 12px; }
    audio { width: 100%; }
    .path { padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: #c4d1df; overflow-wrap: anywhere; font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    .engine-toggle { display: flex; gap: 4px; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 10px; border: 1px solid var(--line); }
    .engine-toggle button { flex: 1; min-height: 32px; border: none; background: transparent; font-size: 12px; }
    .engine-toggle button.active { background: var(--brand); color: #000; }
    @media (max-width: 900px) { header, .grid, .sliders { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="voice">
  <div class="site-menu">
    <div class="site-menu-inner">
      <a class="site-brand" href="/">Zen AI Hub</a>
      <nav class="site-nav">
        <a href="/">Hub</a>
        <a href="/queue">Queue</a>
        <a data-current="1" href="/voice">Voice</a>
        <a href="/whisper">Whisper</a>
      </nav>
    </div>
  </div>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen Voice Pro</div>
        <h1>Voice AI & Cloning.</h1>
        <p>Lokale Sprachausgabe mit Piper (CPU-effizient) oder XTTS v2 (GPU-basiertes Cloning). Alles bleibt zu 100% offline auf diesem System.</p>
      </section>
      <aside class="panel side">
        <label>Engine</label>
        <div class="engine-toggle">
          <button id="enginePiper" class="active">Piper (Fast)</button>
          <button id="engineXTTS">XTTS v2 (Clone)</button>
        </div>
      </aside>
    </header>
    <section class="grid">
      <div class="card">
        <label>Text<textarea id="textInput">Hallo, das ist eine lokale Stimme aus dem Zen AI Hub.</textarea></label>
        <div class="actions"><button class="primary" id="speakBtn">Audio erzeugen</button><button id="clearBtn">Leeren</button></div>
        <div class="status" id="statusLine">Bereit.</div>
      </div>
      <div class="card controls">
        <div id="piperControls">
          <label>Piper Stimme<select id="voiceSelect"></select></label>
          <div class="sliders">
            <label>Tempo <span id="lengthValue">1.00</span><input id="lengthScale" type="range" min="0.70" max="1.50" step="0.01" value="1.00"></label>
            <label>Variation <span id="noiseValue">0.52</span><input id="noiseScale" type="range" min="0.20" max="1.00" step="0.01" value="0.52"></label>
          </div>
        </div>
        <div id="xttsControls" class="hidden">
          <label>Referenz-Stimme (Clone)<select id="speakerSelect"></select></label>
          <label>Sprache<select id="langSelect">
            <option value="de">Deutsch</option>
            <option value="en">Englisch</option>
            <option value="es">Spanisch</option>
            <option value="fr">Franzoesisch</option>
            <option value="it">Italienisch</option>
          </select></label>
          <label>Neue Referenz hochladen (.wav)<input type="file" id="speakerUpload" accept=".wav"></label>
        </div>
        <div class="result" id="resultBox"><audio id="audioPlayer" controls class="hidden"></audio><a class="button-link hidden" id="downloadLink" href="#" download>Download</a><div class="path" id="outputPath">Noch keine Datei erzeugt.</div></div>
      </div>
    </section>
  </main>
  <script>
    let currentEngine = 'piper';
    const elements = {
        voiceSelect: document.getElementById("voiceSelect"),
        speakerSelect: document.getElementById("speakerSelect"),
        statusLine: document.getElementById("statusLine"),
        textInput: document.getElementById("textInput"),
        lengthScale: document.getElementById("lengthScale"),
        noiseScale: document.getElementById("noiseScale"),
        lengthValue: document.getElementById("lengthValue"),
        noiseValue: document.getElementById("noiseValue"),
        audioPlayer: document.getElementById("audioPlayer"),
        downloadLink: document.getElementById("downloadLink"),
        outputPath: document.getElementById("outputPath"),
        piperControls: document.getElementById("piperControls"),
        xttsControls: document.getElementById("xttsControls"),
        enginePiper: document.getElementById("enginePiper"),
        engineXTTS: document.getElementById("engineXTTS"),
        langSelect: document.getElementById("langSelect"),
        speakerUpload: document.getElementById("speakerUpload")
    };

    function setStatus(message) { elements.statusLine.textContent = message; }
    function updateSliderLabels() { elements.lengthValue.textContent = Number(elements.lengthScale.value).toFixed(2); elements.noiseValue.textContent = Number(elements.noiseScale.value).toFixed(2); }
    elements.lengthScale.addEventListener("input", updateSliderLabels); elements.noiseScale.addEventListener("input", updateSliderLabels); updateSliderLabels();

    elements.enginePiper.onclick = () => { currentEngine = 'piper'; elements.enginePiper.classList.add('active'); elements.engineXTTS.classList.remove('active'); elements.piperControls.classList.remove('hidden'); elements.xttsControls.classList.add('hidden'); };
    elements.engineXTTS.onclick = () => { currentEngine = 'xtts'; elements.engineXTTS.classList.add('active'); elements.enginePiper.classList.remove('active'); elements.xttsControls.classList.remove('hidden'); elements.piperControls.classList.add('hidden'); };

    async function api(path, options = {}) { const response = await fetch(path, options); const data = await response.json(); if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`); return data; }
    
    async function loadData() {
        const voices = await api('/api/voices');
        elements.voiceSelect.innerHTML = voices.voices.map(v => `<option value="${v.id}">${v.label}</option>`).join('');
        const speakers = await api('/api/speakers');
        elements.speakerSelect.innerHTML = speakers.speakers.map(s => `<option value="${s}">${s}</option>`).join('');
    }

    elements.speakerUpload.onchange = async () => {
        if (!elements.speakerUpload.files.length) return;
        const file = elements.speakerUpload.files[0];
        const formData = new FormData();
        formData.append('file', file);
        setStatus('Lade Referenz hoch...');
        try {
            await api('/api/speakers/upload', { method: 'POST', body: formData });
            await loadData();
            setStatus('Referenz hochgeladen.');
        } catch (e) { setStatus(`Upload-Fehler: ${e.message}`); }
    };

    async function synthesize() {
        const text = elements.textInput.value.trim();
        if (!text) return;
        elements.speakBtn.disabled = true;
        setStatus('Initialisiere Synthese...');
        try {
            const payload = { text, engine: currentEngine };
            if (currentEngine === 'piper') {
                payload.voice = elements.voiceSelect.value;
                payload.length_scale = Number(elements.lengthScale.value);
                payload.noise_scale = Number(elements.noiseScale.value);
            } else {
                payload.speaker = elements.speakerSelect.value;
                payload.language = elements.langSelect.value;
            }
            const data = await api('/api/synthesize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            elements.audioPlayer.src = data.download_url;
            elements.audioPlayer.classList.remove('hidden');
            elements.downloadLink.href = data.download_url;
            elements.downloadLink.classList.remove('hidden');
            elements.outputPath.textContent = data.output;
            setStatus(`Fertig (${data.duration_ms}ms)`);
        } catch (e) { setStatus(`Fehler: ${e.message}`); }
        finally { elements.speakBtn.disabled = false; }
    }
    document.getElementById('speakBtn').onclick = synthesize;
    loadData().catch(e => setStatus(`Fehler: ${e.message}`));
  </script>
</body>
</html>'''

def voices() -> list[dict[str, Any]]:
    result = []
    for model in sorted(VOICE_DIR.glob('*.onnx')):
        voice_id = model.name.removesuffix('.onnx')
        result.append({
            'id': voice_id,
            'label': VOICE_LABELS.get(voice_id, voice_id),
            'model': str(model),
        })
    return result

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.get('/api/voices')
def list_voices() -> dict[str, Any]:
    return {'voices': voices()}

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

@app.post('/api/synthesize')
def synthesize(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    text = str(payload.get('text') or '').strip()
    engine = str(payload.get('engine') or 'piper')
    stamp = time.strftime('%Y%m%d-%H%M%S')
    
    if engine == 'piper':
        voice = str(payload.get('voice') or 'de_DE-thorsten-medium')
        available = {v['id']: v for v in voices()}
        if voice not in available:
            raise HTTPException(status_code=400, detail=f'Unbekannte Stimme: {voice}')
        out = OUTPUT_DIR / f'{stamp}-piper-{voice}.wav'
        length_scale = float(payload.get('length_scale') or 1.0)
        noise_scale = float(payload.get('noise_scale') or 0.52)
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = f'{PIPER_LIB_DIR}:{env.get("LD_LIBRARY_PATH", "")}'
        cmd = [str(PIPER_BIN), '--model', available[voice]['model'], '--output_file', str(out), '--length_scale', str(length_scale), '--noise_scale', str(noise_scale), '--quiet']
        started = time.time()
        proc = subprocess.run(cmd, input=text, capture_output=True, text=True, env=env, timeout=60)
        duration_ms = round((time.time() - started) * 1000)
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=proc.stderr.strip() or 'Piper Error')
    
    elif engine == 'xtts':
        speaker = str(payload.get('speaker') or '')
        if not speaker:
            raise HTTPException(status_code=400, detail='Referenz-Stimme fehlt.')
        speaker_path = SPEAKER_DIR / speaker
        if not speaker_path.exists():
            raise HTTPException(status_code=404, detail='Referenz-Datei nicht gefunden.')
        
        language = str(payload.get('language') or 'de')
        out = OUTPUT_DIR / f'{stamp}-xtts-{speaker.replace(".wav", "")}.wav'
        
        started = time.time()
        model = get_xtts_model()
        model.tts_to_file(text=text, speaker_wav=str(speaker_path), language=language, file_path=str(out))
        duration_ms = round((time.time() - started) * 1000)
    
    else:
        raise HTTPException(status_code=400, detail=f'Unbekannte Engine: {engine}')

    return {
        'status': 'ok',
        'engine': engine,
        'output': str(out),
        'download_url': f'/api/audio/{out.name}',
        'duration_ms': duration_ms
    }

@app.get('/api/audio/{name}')
def audio(name: str) -> FileResponse:
    path = OUTPUT_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail='Datei nicht gefunden.')
    return FileResponse(path, media_type='audio/wav')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
