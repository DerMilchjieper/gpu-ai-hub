import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

TTS_ROOT = Path('/home/wizzard/ai/tts')
PIPER_BIN = TTS_ROOT / 'bin/piper'
PIPER_LIB_DIR = TTS_ROOT / 'bin'
VOICE_DIR = TTS_ROOT / 'voices'
OUTPUT_DIR = TTS_ROOT / 'outputs'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE_LABELS = {
    'de_DE-thorsten-medium': 'Deutsch - Thorsten medium',
    'de_DE-kerstin-low': 'Deutsch - Kerstin low',
    'de_DE-ramona-low': 'Deutsch - Ramona low',
    'en_US-lessac-medium': 'English - Lessac medium',
    'en_US-hfc_female-medium': 'English - HFC female medium',
}

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Voice</title>
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
    h2, h3 { margin: 0; letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.6; margin: 0; }
    .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(300px, 0.7fr); gap: 14px; }
    .card { padding: 18px; display: grid; gap: 14px; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="range"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
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
    @media (max-width: 900px) { header, .grid, .sliders { grid-template-columns: 1fr; } }
    @media (max-width: 760px) { .site-menu-inner { align-items: stretch; flex-direction: column; padding: 10px 0; } .site-nav { justify-content: flex-start; } .site-nav a { flex: 1 1 auto; } }
  </style>
</head>
<body data-page="voice">
  <div class="site-menu">
    <div class="site-menu-inner">
      <a class="site-brand" data-nav="hub" href="http://192.168.2.41:8191/">Zen AI Hub</a>
      <nav class="site-nav" aria-label="Zen AI Hub Navigation">
        <a data-nav="hub" href="http://192.168.2.41:8191/">Hub</a>
        <a data-nav="queue" href="http://192.168.2.41:11435/status">GPU Queue</a>
        <a data-nav="voice" href="http://192.168.2.41:8002/">Voice</a>
        <a data-nav="whisper" href="http://192.168.2.41:8000/">Whisper</a>
        <a data-nav="workspace" href="http://192.168.2.41:8001/?workspace=1">Workspace</a>
        <a data-nav="comfy" href="http://192.168.2.41:8188/" target="_blank" rel="noreferrer">ComfyUI</a>
      </nav>
    </div>
  </div>
  <script>
    (() => {
      const host = window.location.hostname || "192.168.2.41";
      const urls = { hub: `http://${host}:8191/`, queue: `http://${host}:11435/status`, voice: `http://${host}:8002/`, whisper: `http://${host}:8000/`, workspace: `http://${host}:8001/?workspace=1`, comfy: `http://${host}:8188/` };
      document.querySelectorAll("[data-nav]").forEach((link) => { const key = link.dataset.nav; if (urls[key]) link.href = urls[key]; });
      const active = document.body.dataset.page;
      document.querySelectorAll(`[data-nav="${active}"]`).forEach((link) => { link.dataset.current = "1"; });
    })();
  </script>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen Voice</div>
        <h1>Lokale Sprachausgabe.</h1>
        <p>Piper TTS laeuft vollstaendig offline auf diesem Ubuntu-System. Texte werden lokal als WAV erzeugt; Cloud-Dienste sind fuer diese Stufe nicht beteiligt.</p>
      </section>
      <aside class="panel side">
        <span class="badge">Piper offline</span>
        <p>Naechste Ausbaustufe: XTTS/OpenVoice als GPU-Queue-Job fuer Voice-Cloning mit freigegebenen Referenzaufnahmen.</p>
      </aside>
    </header>
    <section class="grid">
      <div class="card">
        <label>Text<textarea id="textInput">Hallo, das ist eine lokale Piper-Stimme aus dem Zen AI Hub.</textarea></label>
        <div class="actions"><button class="primary" id="speakBtn">WAV erzeugen</button><button id="clearBtn">Leeren</button></div>
        <div class="status" id="statusLine">Bereit.</div>
      </div>
      <div class="card controls">
        <label>Stimme<select id="voiceSelect"></select></label>
        <div class="sliders">
          <label>Tempo <span id="lengthValue">1.00</span><input id="lengthScale" type="range" min="0.70" max="1.50" step="0.01" value="1.00"></label>
          <label>Variation <span id="noiseValue">0.52</span><input id="noiseScale" type="range" min="0.20" max="1.00" step="0.01" value="0.52"></label>
        </div>
        <div class="result" id="resultBox"><audio id="audioPlayer" controls class="hidden"></audio><a class="button-link hidden" id="downloadLink" href="#" download>Download WAV</a><div class="path" id="outputPath">Noch keine Datei erzeugt.</div></div>
      </div>
    </section>
  </main>
  <script>
    const voiceSelect = document.getElementById("voiceSelect");
    const statusLine = document.getElementById("statusLine");
    const textInput = document.getElementById("textInput");
    const lengthScale = document.getElementById("lengthScale");
    const noiseScale = document.getElementById("noiseScale");
    const lengthValue = document.getElementById("lengthValue");
    const noiseValue = document.getElementById("noiseValue");
    const audioPlayer = document.getElementById("audioPlayer");
    const downloadLink = document.getElementById("downloadLink");
    const outputPath = document.getElementById("outputPath");
    function setStatus(message) { statusLine.textContent = message; }
    function updateSliderLabels() { lengthValue.textContent = Number(lengthScale.value).toFixed(2); noiseValue.textContent = Number(noiseScale.value).toFixed(2); }
    lengthScale.addEventListener("input", updateSliderLabels); noiseScale.addEventListener("input", updateSliderLabels); updateSliderLabels();
    async function api(path, options = {}) { const response = await fetch(path, options); const text = await response.text(); let data = {}; try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; } if (!response.ok) throw new Error(data.detail || data.raw || `HTTP ${response.status}`); return data; }
    async function loadVoices() { const data = await api('/api/voices'); voiceSelect.innerHTML = data.voices.map((voice) => `<option value="${voice.id}">${voice.label}</option>`).join(''); const preferred = data.voices.find((voice) => voice.id.includes('thorsten')) || data.voices[0]; if (preferred) voiceSelect.value = preferred.id; }
    async function synthesize(event) { const button = event.currentTarget; const text = textInput.value.trim(); if (!text) return; const oldText = button.textContent; button.disabled = true; button.textContent = 'Erzeuge...'; setStatus('Piper erzeugt lokal eine WAV-Datei...'); try { const data = await api('/api/synthesize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, voice: voiceSelect.value, length_scale: Number(lengthScale.value), noise_scale: Number(noiseScale.value) }) }); audioPlayer.src = data.download_url; audioPlayer.classList.remove('hidden'); downloadLink.href = data.download_url; downloadLink.classList.remove('hidden'); outputPath.textContent = data.output; setStatus(`Fertig: ${data.voice}, ${data.duration_ms} ms.`); } catch (error) { setStatus(`Fehler: ${error.message}`); } finally { button.disabled = false; button.textContent = oldText; } }
    document.getElementById('speakBtn').addEventListener('click', synthesize);
    document.getElementById('clearBtn').addEventListener('click', () => { textInput.value = ''; textInput.focus(); });
    loadVoices().catch((error) => setStatus(`Stimmen konnten nicht geladen werden: ${error.message}`));
  </script>
</body>
</html>'''


def voice_id_from_model(path: Path) -> str:
    return path.name.removesuffix('.onnx')


def voices() -> list[dict[str, Any]]:
    result = []
    for model in sorted(VOICE_DIR.glob('*.onnx')):
        voice_id = voice_id_from_model(model)
        result.append({
            'id': voice_id,
            'label': VOICE_LABELS.get(voice_id, voice_id),
            'model': str(model),
            'config': str(model) + '.json',
            'language': voice_id.split('-', 1)[0],
        })
    return result


def safe_slug(value: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_-]+', '_', value).strip('_')
    return slug[:48] or 'voice'


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get('/api/voices')
def list_voices() -> dict[str, Any]:
    found = voices()
    if not found:
        raise HTTPException(status_code=500, detail=f'Keine Piper-Stimmen in {VOICE_DIR} gefunden.')
    return {'status': 'ok', 'voices': found}


@app.post('/api/synthesize')
def synthesize(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    text = str(payload.get('text') or '').strip()
    if not text:
        raise HTTPException(status_code=400, detail='Text fehlt.')
    voice = str(payload.get('voice') or 'de_DE-thorsten-medium')
    available = {entry['id']: entry for entry in voices()}
    if voice not in available:
        raise HTTPException(status_code=400, detail=f'Unbekannte Stimme: {voice}')
    if not PIPER_BIN.exists():
        raise HTTPException(status_code=500, detail=f'Piper fehlt: {PIPER_BIN}')
    length_scale = float(payload.get('length_scale') or 1.0)
    noise_scale = float(payload.get('noise_scale') or 0.52)
    noise_w = float(payload.get('noise_w') or 0.55)
    sentence_silence = float(payload.get('sentence_silence') or 0.35)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    out = OUTPUT_DIR / f'{stamp}-{safe_slug(voice)}.wav'
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = f'{PIPER_LIB_DIR}:{env.get("LD_LIBRARY_PATH", "")}'
    cmd = [str(PIPER_BIN), '--model', available[voice]['model'], '--output_file', str(out), '--length_scale', str(length_scale), '--noise_scale', str(noise_scale), '--noise_w', str(noise_w), '--sentence_silence', str(sentence_silence), '--quiet']
    started = time.time()
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True, env=env, timeout=300)
    duration_ms = round((time.time() - started) * 1000)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr.strip() or proc.stdout.strip() or 'Piper fehlgeschlagen.')
    return {'status': 'ok', 'engine': 'piper', 'voice': voice, 'output': str(out), 'download_url': f'/api/audio/{out.name}', 'duration_ms': duration_ms}


@app.get('/api/audio/{name}')
def audio(name: str) -> FileResponse:
    if '/' in name or '..' in name:
        raise HTTPException(status_code=400, detail='Ungueltiger Dateiname.')
    path = OUTPUT_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail='Datei nicht gefunden.')
    return FileResponse(path, media_type='audio/wav', filename=name)


@app.get('/api/status')
def status() -> dict[str, Any]:
    return {'status': 'ok', 'engine': 'piper', 'piper': str(PIPER_BIN), 'voices': len(voices()), 'output_dir': str(OUTPUT_DIR)}
