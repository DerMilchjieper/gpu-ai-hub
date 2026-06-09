import json
import time
import requests
from typing import Any, List
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

OLLAMA_API = "http://127.0.0.1:11435/api/chat"
DEFAULT_MODEL = "qwen3:8b"

SYSTEM_PROMPT = """Du bist 'Zen Prompt Master', ein weltweit führender Experte für ComfyUI Prompt Engineering. 
Deine Aufgabe ist es, die oft chaotischen, beschreibenden oder unstrukturierten Erklärungen des Nutzers ("Gebrabbel") zu verstehen und in hochgradig optimierte Prompts für lokale KI-Modelle zu übersetzen.

Du kennst die folgenden lokalen Workflows und Modelle perfekt:
1. **Text to Image (SDXL/Flux):** (`text_to_image_preload_clean.json`) - Für hochwertige Standbilder. Flux mag Storytelling, SDXL mag gewichtete Tags.
2. **Wan2.2 Video (Text-to-Video):** (`text_to_image_to_wan_i2v_video.json`) - Erzeugt Videos. Braucht Bewegungshinweise.
3. **Stable Fast 3D (SF3D):** (`stable_fast_3d_image_to_3d.json`) - Macht aus einem Bild ein 3D-Modell (GLB).
4. **Text to SF3D (Full Pipeline):** (`text_to_image_to_sf3d_glb.json`) - Erzeugt erst ein Bild und dann direkt das 3D-Mesh.
5. **TripoSR 3D:** (`triposr_image_to_3d.json`) - Schnellerer Fallback für 3D (OBJ).
6. **Video Upscale:** (`video_upscale_2x_lanczos.json`) - Skaliert Videos auf 2x Auflösung hoch.

DEIN WORKFLOW:
- Höre dem Nutzer zu, egal wie unstrukturiert er redet.
- Extrahiere das Kern-Thema, den Stil, das Licht und die Stimmung.
- **SPRACH-REGEL:** Deine Erklärungen sind auf DEUTSCH. Der fertige, optimierte Prompt im Block MUSS jedoch zwingend auf ENGLISCH sein (für maximale Modell-Kompatibilität).
- Gib ihm in deiner Antwort eine kurze Erklärung, welchen Workflow du empfiehlst und was du am Prompt optimiert hast.
- **WICHTIG:** Gib am Ende deiner Antwort den fertigen ENGLISCHEN Prompt in einem klar markierten Block aus, den man leicht kopieren kann.

Verhalte dich wie ein kreativer Partner, nicht wie ein stumpfer Übersetzer. Wenn Informationen fehlen (z.B. das Format oder der Kunststil), frage höflich nach oder schlage eine passende Option vor."""

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Prompt</title>
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
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    .chat-box { flex: 1; display: flex; flex-direction: column; gap: 14px; min-height: 500px; max-height: 65vh; overflow-y: auto; padding-right: 8px; margin-bottom: 14px; }
    .chat-msg { padding: 16px; border-radius: 12px; line-height: 1.6; font-size: 14px; position: relative; }
    .chat-msg.user { background: rgba(85,214,189,0.12); border: 1px solid rgba(85,214,189,0.2); align-self: flex-end; max-width: 85%; }
    .chat-msg.ai { background: rgba(255,255,255,0.05); border: 1px solid var(--line); align-self: flex-start; max-width: 90%; }
    .prompt-block { background: #000; padding: 14px; border-radius: 8px; border: 1px solid var(--brand); margin: 10px 0; font-family: monospace; font-size: 13px; color: var(--brand); white-space: pre-wrap; cursor: pointer; position: relative; }
    .prompt-block:hover::after { content: "Klicken zum Kopieren"; position: absolute; top: -20px; right: 0; font-size: 10px; color: var(--muted); }
    .status { color: var(--muted); min-height: 24px; font-size: 13px; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="prompt">
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
        {id: "workspace", label: "Workspace"},
        {id: "comfy", label: "ComfyUI", target: "_blank"}
      ];
      nav.innerHTML = links.map(l => `<a data-nav="${l.id}" href="${urls[l.id]}" ${l.target ? `target="${l.target}"` : ''}>${l.label}</a>`).join('');
      document.querySelectorAll(`[data-nav="prompt"]`).forEach((link) => { link.dataset.current = "1"; });
    })();
  </script>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen Prompt</div>
        <h1>ComfyUI Prompt Expert.</h1>
        <p>Erzaehle mir deine Idee, egal wie wirr. Ich uebersetze sie in den perfekten Prompt fuer FLUX, SDXL oder Video-Modelle.</p>
      </section>
      <aside class="panel side">
        <label>LLM Engine<select id="modelSelect">
          <option value="qwen3:8b">Qwen 3 (8B) - Balanced</option>
          <option value="llama3.1:latest">Llama 3.1 (8B)</option>
          <option value="qwen3.6:27b">Qwen 3.6 (27B) - Expert</option>
        </select></label>
      </aside>
    </header>
    <section class="grid">
      <div class="card controls" style="display:flex; flex-direction:column;">
        <div class="chat-box" id="chatBox">
            <div class="chat-msg ai">Hallo! Was schwebt dir vor? Beschreibe mir dein Bild oder Video einfach so, wie es dir in den Sinn kommt.</div>
        </div>
        <div style="display:flex; gap:10px; align-items:end;">
            <textarea id="chatInput" placeholder="Mein Gebrabbel hier rein... (z.B. Ein Cyberpunk Ritter der auf einem Drachen durch Berlin fliegt, alles im Neon-Stil)"></textarea>
            <button class="primary" id="sendBtn" style="height: 80px; width: 100px;">Senden</button>
        </div>
        <div class="status" id="statusLine">Bereit.</div>
      </div>
      
      <div class="card" id="outputCard">
        <label>Optimierte Prompts</label>
        <div id="promptsContainer" style="display:grid; gap:12px;">
            <p style="font-size:13px; color:var(--muted)">Hier erscheinen die fertigen Blöcke zum Kopieren.</p>
        </div>
        <span class="badge" id="timeBadge">-</span>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        chatBox: document.getElementById("chatBox"),
        chatInput: document.getElementById("chatInput"),
        sendBtn: document.getElementById("sendBtn"),
        modelSelect: document.getElementById("modelSelect"),
        statusLine: document.getElementById("statusLine"),
        promptsContainer: document.getElementById("promptsContainer"),
        timeBadge: document.getElementById("timeBadge")
    };

    let chatHistory = [];

    function appendMsg(role, text) {
        const div = document.createElement("div");
        div.className = `chat-msg ${role}`;
        
        // Detect prompt blocks (anything in ``` or just looking like a prompt)
        let formattedText = text.replace(/```([\s\S]*?)```/g, (match, p1) => {
            return `<div class="prompt-block" onclick="copyToClipboard(this)">${p1.trim()}</div>`;
        });
        
        div.innerHTML = formattedText.replace(/\n/g, "<br>");
        elements.chatBox.appendChild(div);
        elements.chatBox.scrollTop = elements.chatBox.scrollHeight;
        
        // Extract prompt blocks to the right card too
        const blocks = div.querySelectorAll(".prompt-block");
        if(blocks.length > 0) {
            elements.promptsContainer.innerHTML = '';
            blocks.forEach(b => {
                const clone = b.cloneNode(true);
                elements.promptsContainer.appendChild(clone);
            });
        }
        
        return div;
    }

    window.copyToClipboard = (el) => {
        navigator.clipboard.writeText(el.innerText).then(() => {
            const originalColor = el.style.borderColor;
            el.style.borderColor = "var(--brand-2)";
            setTimeout(() => el.style.borderColor = originalColor, 500);
        });
    };

    elements.sendBtn.onclick = async () => {
        const input = elements.chatInput.value.trim();
        if(!input) return;
        
        elements.chatInput.value = '';
        elements.sendBtn.disabled = true;
        appendMsg('user', input);
        chatHistory.push({role: 'user', content: input});
        
        elements.statusLine.textContent = 'Zen Prompt Master denkt nach...';
        const startTime = Date.now();
        
        try {
            const res = await fetch('/api/prompt/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    history: chatHistory, 
                    model: elements.modelSelect.value 
                })
            });
            const data = await res.json();
            if(!res.ok) throw new Error(data.detail);
            
            appendMsg('ai', data.response);
            chatHistory.push({role: 'assistant', content: data.response});
            
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            elements.statusLine.textContent = `Fertig in ${duration}s`;
            elements.timeBadge.textContent = `${duration}s`;
            
        } catch(e) {
            elements.statusLine.textContent = `Fehler: ${e.message}`;
        } finally {
            elements.sendBtn.disabled = false;
        }
    };

    elements.chatInput.onkeydown = (e) => {
        if(e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            elements.sendBtn.click();
        }
    };
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.post('/api/prompt/chat')
def chat(payload: dict = Body(...)):
    history = payload.get('history', [])
    model = payload.get('model', DEFAULT_MODEL)
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    
    try:
        response = requests.post(
            OLLAMA_API,
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.8 # Higher creativity for prompt engineering
                }
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        return {"response": data.get("message", {}).get("content", "")}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
