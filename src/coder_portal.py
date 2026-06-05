import json
import time
from typing import Any

import requests
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

OLLAMA_API_BASE = "http://127.0.0.1:11435"

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Coder</title>
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
    .grid { display: grid; grid-template-columns: minmax(350px, 0.4fr) minmax(0, 1fr); gap: 14px; }
    .card { padding: 18px; display: grid; gap: 14px; align-content: start; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    textarea { min-height: 300px; resize: vertical; line-height: 1.5; font-family: "Cascadia Mono", Consolas, monospace; font-size: 13px; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    
    .chat-box { flex: 1; display: flex; flex-direction: column; gap: 14px; min-height: 400px; max-height: 70vh; overflow-y: auto; padding-right: 8px; margin-bottom: 14px; }
    .chat-msg { padding: 16px; border-radius: 8px; background: rgba(255,255,255,0.05); line-height: 1.6; word-wrap: break-word; font-size: 14px; }
    .chat-msg.user { background: rgba(85,214,189,0.1); border-left: 3px solid var(--brand); }
    .chat-msg.ai { background: rgba(0,0,0,0.2); border-left: 3px solid var(--brand-2); font-family: "Cascadia Mono", Consolas, monospace; }
    
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="coder">
  <div class="site-menu">
    <div class="site-menu-inner">
      <a class="site-brand" data-nav="hub" href="http://192.168.2.41:8191/">Zen AI Hub</a>
      <nav class="site-nav" aria-label="Zen AI Hub Navigation">
        <a data-nav="hub" href="http://192.168.2.41:8191/">Hub</a>
        <a data-nav="queue" href="http://192.168.2.41:11435/status">GPU Queue</a>
        <a data-nav="vision" href="http://192.168.2.41:8003/">Vision</a>
        <a data-nav="voice" href="http://192.168.2.41:8002/">Voice Pro</a>
        <a data-nav="docs" href="http://192.168.2.41:8004/">Docs</a>
        <a data-nav="video" href="http://192.168.2.41:8005/">Video Lab</a>
        <a data-nav="coder" href="http://192.168.2.41:8006/">Coder</a>
        <a data-nav="auto" href="http://192.168.2.41:8007/">Automator</a>
        <a data-nav="whisper" href="http://192.168.2.41:8000/">Whisper</a>
        <a data-nav="workspace" href="http://192.168.2.41:8001/?workspace=1">Workspace</a>
        <a data-nav="comfy" href="http://192.168.2.41:8188/" target="_blank" rel="noreferrer">ComfyUI</a>
      </nav>
    </div>
  </div>
  <script>
    (() => {
      const host = window.location.hostname || "192.168.2.41";
      const urls = { hub: `http://${host}:8191/`, queue: `http://${host}:11435/status`, vision: `http://${host}:8003/`, voice: `http://${host}:8002/`, docs: `http://${host}:8004/`, video: `http://${host}:8005/`, coder: `http://${host}:8006/`, auto: `http://${host}:8007/`, whisper: `http://${host}:8000/`, workspace: `http://${host}:8001/?workspace=1`, comfy: `http://${host}:8188/` };
      document.querySelectorAll("[data-nav]").forEach((link) => { const key = link.dataset.nav; if (urls[key]) link.href = urls[key]; });
      const active = document.body.dataset.page;
      document.querySelectorAll(`[data-nav="${active}"]`).forEach((link) => { link.dataset.current = "1"; });
    })();
  </script>
  <main class="shell">
    <header>
      <section class="panel hero">
        <div class="eyebrow">Zen Coder</div>
        <h1>Local AI Code Assistant.</h1>
        <p>Refaktoriere Code, finde Bugs oder lass dir komplexe Zusammenhaenge erklaeren. Nutzt spezielle Coder-Modelle (DeepSeek, Qwen2.5) fuer beste Ergebnisse.</p>
      </section>
      <aside class="panel side">
        <label>Coder Model<select id="modelSelect">
          <option value="qwen2.5-coder:32b-instruct-q4_K_S">Qwen 2.5 Coder (32B)</option>
          <option value="qwen2.5-coder:14b">Qwen 2.5 Coder (14B)</option>
          <option value="deepseek-coder-v2:16b">DeepSeek Coder v2 (16B)</option>
        </select></label>
      </aside>
    </header>
    <section class="grid">
      <div class="card">
        <label>Code Snippet<textarea id="codeInput" placeholder="Fuege hier deinen Code ein..."></textarea></label>
        <label>Anweisung<input type="text" id="promptInput" value="Finde den Fehler und optimiere den Code."></label>
        <div class="actions">
          <button class="primary" id="askBtn">Code analysieren</button>
        </div>
      </div>
      
      <div class="card controls" style="display:flex; flex-direction:column;">
        <div class="chat-box" id="chatBox">
            <div class="chat-msg ai">Bereit. Welchen Code soll ich ueberpruefen?</div>
        </div>
        <span class="badge" id="timeBadge">Warte auf Input...</span>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        modelSelect: document.getElementById("modelSelect"),
        codeInput: document.getElementById("codeInput"),
        promptInput: document.getElementById("promptInput"),
        askBtn: document.getElementById("askBtn"),
        chatBox: document.getElementById("chatBox"),
        timeBadge: document.getElementById("timeBadge")
    };

    function appendMsg(role, text) {
        const div = document.createElement("div");
        div.className = `chat-msg ${role}`;
        
        // Very basic escaping
        let safeText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        
        // Simple markdown code block rendering
        if(role === 'ai') {
            safeText = safeText.replace(/```(.*?)\n([\s\S]*?)```/g, '<div style="background:#000; padding:10px; border-radius:6px; margin:8px 0; overflow-x:auto;">$2</div>');
        }
        
        div.innerHTML = safeText.replace(/\n/g, "<br>");
        elements.chatBox.appendChild(div);
        elements.chatBox.scrollTop = elements.chatBox.scrollHeight;
        return div;
    }

    elements.askBtn.onclick = async () => {
        const code = elements.codeInput.value.trim();
        const instruction = elements.promptInput.value.trim();
        if(!code && !instruction) return;
        
        appendMsg('user', `Code:\n${code.substring(0, 100)}...\n\nAnweisung: ${instruction}`);
        elements.askBtn.disabled = true;
        
        const aiMsg = appendMsg('ai', 'Analysiere Code...');
        elements.timeBadge.textContent = 'Berechnet...';
        
        const sys_prompt = `${instruction}\n\nHier ist der Code:\n\`\`\`\n${code}\n\`\`\``;
        const startTime = Date.now();
        
        try {
            const res = await fetch('/api/coder/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ prompt: sys_prompt, model: elements.modelSelect.value })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            
            // Re-render HTML with new text
            let safeText = data.response.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            safeText = safeText.replace(/```(.*?)\n([\s\S]*?)```/g, '<div style="background:#000; padding:10px; border-radius:6px; margin:8px 0; overflow-x:auto;">$2</div>');
            aiMsg.innerHTML = safeText.replace(/\n/g, "<br>");
            
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            elements.timeBadge.textContent = `${duration}s (${data.tokens_per_second || 0} t/s)`;
            
        } catch (e) {
            aiMsg.textContent = `Fehler: ${e.message}`;
            elements.timeBadge.textContent = 'Fehler';
        } finally {
            elements.askBtn.disabled = false;
        }
    };
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.post('/api/coder/chat')
def chat(payload: dict = Body(...)):
    prompt = payload.get('prompt')
    model = payload.get('model', 'qwen2.5-coder:14b')
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Kein Prompt.")
        
    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
