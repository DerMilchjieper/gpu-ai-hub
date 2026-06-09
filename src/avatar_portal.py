import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Avatar</title>
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
    .grid { display: grid; grid-template-columns: minmax(400px, 0.45fr) minmax(0, 1fr); gap: 14px; }
    .card { padding: 18px; display: grid; gap: 14px; align-content: start; }
    .alert { background: rgba(246,195,109,0.1); border: 1px solid var(--brand-2); color: #fff; padding: 16px; border-radius: 8px; font-size: 14px; line-height: 1.5; }
    .alert code { background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; color: var(--brand-2); }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; width: 100%; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    iframe { width: 100%; height: 800px; border: 1px solid var(--line); border-radius: 8px; background: #000; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="avatar">
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
        {id: "avatar", label: "Avatar Live"},
        {id: "prompt", label: "Prompt Expert"},
        {id: "gallery", label: "Gallery"},
        {id: "audio", label: "Audio"},
        {id: "system", label: "System"},
        {id: "queue", label: "GPU Queue"},
        {id: "vision", label: "Vision"},
        {id: "voice", label: "Voice Pro"},
        {id: "docs", label: "Docs"},
        {id: "video", label: "Video Lab"},
        {id: "coder", label: "Coder"},
        {id: "auto", label: "Automator"},
        {id: "n8n", label: "n8n", target: "_blank"},
        {id: "whisper", label: "Whisper"},
        {id: "comfy", label: "ComfyUI", target: "_blank"}
      ];
      nav.innerHTML = links.map(l => `<a data-nav="${l.id}" href="${urls[l.id]}" ${l.target ? `target="${l.target}"` : ''}>${l.label}</a>`).join('');
      document.querySelectorAll(`[data-nav="avatar"]`).forEach((link) => { link.dataset.current = "1"; });
      
      // Also update the FaceFusion iframe src dynamically
      window.onload = () => {
          document.getElementById('ffIframe').src = `http://${host}:8014/`;
          document.getElementById('ffLink').href = `http://${host}:8014/`;
      };
    })();
  </script>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen Avatar</div>
        <h1>Real-Time FaceFusion.</h1>
        <p>Verwandle dein Gesicht live über deine Laptop-Webcam. Das Bild wird in Echtzeit über das Netzwerk an die RTX 3090 gestreamt (WebRTC) und dort durch das KI-Gesicht ersetzt.</p>
      </section>
      <aside class="panel side">
        <a id="ffLink" href="http://192.168.2.41:8014" target="_blank" class="button primary">Im Vollbild oeffnen (Empfohlen)</a>
      </aside>
    </header>
    
    <div class="alert" style="margin-bottom: 20px;">
      <strong>WICHTIG für den Webcam-Zugriff:</strong><br>
      Da dieser Hub im lokalen Netzwerk (HTTP) läuft, blockiert der Browser (Chrome/Edge) den Kamera-Zugriff aus Sicherheitsgründen.<br><br>
      <strong>Lösung (Einmalig auf dem Laptop):</strong><br>
      1. Öffne <code>chrome://flags/#unsafely-treat-insecure-origin-as-secure</code><br>
      2. Trage exakt dies ein (mit Komma getrennt):<br>
      <code>http://192.168.2.41:8013, http://192.168.2.41:8014</code><br>
      3. Rechts daneben auf <strong>"Enabled"</strong> stellen.<br>
      4. Unten auf <strong>"Relaunch"</strong> klicken.<br><br>
      <em>Hinweis: Wenn es dann immer noch nicht geht, prüfe ob eine andere App (Zoom/Teams) die Kamera blockiert.</em>
    </div>

    <section>
      <iframe id="ffIframe" src="http://192.168.2.41:8014" allow="camera; microphone; autoplay; fullscreen" title="FaceFusion"></iframe>
    </section>
  </main>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
