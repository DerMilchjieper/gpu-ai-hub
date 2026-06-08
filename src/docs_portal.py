import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, List

import requests
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

app = FastAPI()

OLLAMA_API_BASE = "http://127.0.0.1:11435"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen3:8b"

DB_DIR = Path("/home/wizzard/ai/docs/data")
DB_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DB_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

class OllamaEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            try:
                res = requests.post(
                    f"{OLLAMA_API_BASE}/api/embeddings",
                    json={"model": EMBED_MODEL, "prompt": text},
                    timeout=60
                )
                res.raise_for_status()
                embeddings.append(res.json().get("embedding", []))
            except Exception as e:
                print(f"Embedding error: {e}")
                embeddings.append([])
        return embeddings

chroma_client = chromadb.PersistentClient(path=str(DB_DIR / "chromadb"))
embed_fn = OllamaEmbeddingFunction()
collection = chroma_client.get_or_create_collection(name="zen_docs", embedding_function=embed_fn)

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Docs</title>
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
    .grid { display: grid; grid-template-columns: minmax(300px, 0.35fr) minmax(0, 1fr); gap: 14px; }
    .card { padding: 18px; display: grid; gap: 14px; }
    label { display: grid; gap: 8px; color: var(--muted); font-size: 14px; font-weight: 700; }
    textarea, select, input[type="text"] { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.045); color: var(--text); padding: 12px 14px; font: inherit; }
    textarea { min-height: 80px; resize: vertical; line-height: 1.5; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    button, .button-link { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; padding: 0 15px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,0.055); color: var(--text); font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
    .primary { background: #1f8f7a; color: #06100e; border-color: rgba(85,214,189,0.55); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .hidden { display: none !important; }
    .status { color: var(--muted); min-height: 24px; }
    .badge { display: inline-flex; align-items: center; width: fit-content; padding: 7px 10px; border-radius: 8px; background: rgba(85,214,189,0.13); color: var(--brand); font-size: 13px; font-weight: 800; }
    label.file-picker { display: block; border: 1px dashed rgba(255,255,255,0.2); padding: 24px; text-align: center; cursor: pointer; transition: background 0.2s; }
    label.file-picker:hover { background: rgba(255,255,255,0.08); }
    label.file-picker input { display: none; }
    
    .chat-box { flex: 1; display: flex; flex-direction: column; gap: 14px; min-height: 500px; max-height: 60vh; overflow-y: auto; padding-right: 8px; margin-bottom: 14px; }
    .chat-msg { padding: 14px; border-radius: 8px; background: rgba(255,255,255,0.05); line-height: 1.5; word-wrap: break-word; }
    .chat-msg.user { background: rgba(85,214,189,0.1); border-left: 3px solid var(--brand); }
    .chat-msg.ai { background: rgba(0,0,0,0.2); border-left: 3px solid var(--brand-2); }
    .docs-list { font-size: 13px; max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px; }
    .docs-list div { padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text); }
    
    @media (max-width: 900px) { header, .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body data-page="docs">
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
        <div class="eyebrow">Zen Docs</div>
        <h1>Private RAG Chat.</h1>
        <p>Lade PDFs oder Textdokumente hoch. Sie werden lokal vektorisiert und du kannst mit deinem Wissen chatten. Nichts verlaesst dieses System.</p>
      </section>
      <aside class="panel side">
        <label>Chat Model<select id="modelSelect">
          <option value="qwen3:8b">Qwen3 (8B)</option>
          <option value="llama3:latest">Llama 3 (8B)</option>
          <option value="phi3.5:latest">Phi-3.5 (Mini)</option>
        </select></label>
      </aside>
    </header>
    <section class="grid">
      <div class="card" style="align-content: start;">
        <label class="file-picker">
          <input type="file" id="docUpload" accept="application/pdf, text/plain">
          Dokument hochladen (PDF/TXT)
        </label>
        <div class="status" id="uploadStatus"></div>
        <div style="margin-top: 20px;">
            <label>Indizierte Dokumente</label>
            <div class="docs-list" id="docsList">Lade Dokumente...</div>
            <button class="secondary" style="margin-top:10px; width: 100%;" id="clearDbBtn">Datenbank leeren</button>
        </div>
      </div>
      
      <div class="card controls" style="display:flex; flex-direction:column;">
        <div class="chat-box" id="chatBox">
            <div class="chat-msg ai">Hallo! Lade ein Dokument hoch und stelle mir eine Frage dazu.</div>
        </div>
        <div style="display:flex; gap:10px; align-items:end;">
            <textarea id="promptInput" placeholder="Stelle eine Frage zu deinen Dokumenten..."></textarea>
            <button class="primary" id="askBtn" style="height: 80px;">Fragen</button>
        </div>
      </div>
    </section>
  </main>
  <script>
    const elements = {
        modelSelect: document.getElementById("modelSelect"),
        docUpload: document.getElementById("docUpload"),
        uploadStatus: document.getElementById("uploadStatus"),
        docsList: document.getElementById("docsList"),
        chatBox: document.getElementById("chatBox"),
        promptInput: document.getElementById("promptInput"),
        askBtn: document.getElementById("askBtn"),
        clearDbBtn: document.getElementById("clearDbBtn")
    };

    function appendMsg(role, text) {
        const div = document.createElement("div");
        div.className = `chat-msg ${role}`;
        div.textContent = text;
        elements.chatBox.appendChild(div);
        elements.chatBox.scrollTop = elements.chatBox.scrollHeight;
        return div;
    }

    async function loadDocs() {
        try {
            const res = await fetch('/api/docs');
            const data = await res.json();
            const docs = data.documents || [];
            if(docs.length === 0) {
                elements.docsList.innerHTML = "<div>Keine Dokumente gefunden.</div>";
            } else {
                elements.docsList.innerHTML = docs.map(d => `<div>📄 ${d}</div>`).join('');
            }
        } catch (e) {
            elements.docsList.innerHTML = `<div>Fehler: ${e.message}</div>`;
        }
    }

    elements.docUpload.onchange = async () => {
        if (!elements.docUpload.files.length) return;
        const file = elements.docUpload.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        elements.uploadStatus.textContent = 'Lade hoch und indiziere (das kann etwas dauern)...';
        elements.docUpload.disabled = true;
        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            elements.uploadStatus.textContent = `Erfolgreich! ${data.chunks} Abschnitte indiziert.`;
            await loadDocs();
        } catch (e) {
            elements.uploadStatus.textContent = `Fehler: ${e.message}`;
        } finally {
            elements.docUpload.disabled = false;
        }
    };

    elements.clearDbBtn.onclick = async () => {
        if(!confirm("Wirklich alle Dokumente aus der lokalen Datenbank loeschen?")) return;
        try {
            await fetch('/api/clear', { method: 'POST' });
            elements.uploadStatus.textContent = 'Datenbank geleert.';
            await loadDocs();
        } catch (e) {
            elements.uploadStatus.textContent = `Fehler: ${e.message}`;
        }
    };

    elements.askBtn.onclick = async () => {
        const question = elements.promptInput.value.trim();
        if(!question) return;
        
        appendMsg('user', question);
        elements.promptInput.value = '';
        elements.askBtn.disabled = true;
        
        const aiMsg = appendMsg('ai', 'Denke nach...');
        
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ prompt: question, model: elements.modelSelect.value })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            
            aiMsg.innerHTML = data.response;
            if(data.sources && data.sources.length > 0) {
                aiMsg.innerHTML += `<br><br><small style="color:var(--muted)">Quellen: ${data.sources.join(', ')}</small>`;
            }
        } catch (e) {
            aiMsg.textContent = `Fehler: ${e.message}`;
        } finally {
            elements.askBtn.disabled = false;
            elements.promptInput.focus();
        }
    };
    
    elements.promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            elements.askBtn.click();
        }
    });

    loadDocs();
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.get('/api/docs')
def list_docs() -> dict:
    result = collection.get(include=["metadatas"])
    metadatas = result.get("metadatas", [])
    if not metadatas:
        return {"documents": []}
    
    docs = set()
    for m in metadatas:
        if m and "source" in m:
            filename = Path(m["source"]).name
            docs.add(filename)
            
    return {"documents": sorted(list(docs))}

@app.post('/api/clear')
def clear_db():
    chroma_client.delete_collection(name="zen_docs")
    global collection
    collection = chroma_client.get_or_create_collection(name="zen_docs", embedding_function=embed_fn)
    return {"status": "ok"}

@app.post('/api/upload')
async def upload_doc(file: UploadFile = File(...)):
    if not file.filename.endswith(('.pdf', '.txt')):
        raise HTTPException(status_code=400, detail="Nur .pdf und .txt erlaubt.")
        
    path = UPLOAD_DIR / file.filename
    with open(path, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        if file.filename.endswith('.pdf'):
            loader = PyPDFLoader(str(path))
        else:
            loader = TextLoader(str(path))
            
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        if not splits:
            raise HTTPException(status_code=400, detail="Konnte keinen Text extrahieren.")
            
        texts = [s.page_content for s in splits]
        metadatas = [s.metadata for s in splits]
        ids = [f"{file.filename}_{i}" for i in range(len(splits))]
        
        collection.add(documents=texts, metadatas=metadatas, ids=ids)
        return {"status": "ok", "filename": file.filename, "chunks": len(splits)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/chat')
def chat(payload: dict = Body(...)):
    prompt = payload.get('prompt')
    model = payload.get('model', CHAT_MODEL)
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Kein Prompt.")
        
    # Query Chroma
    results = collection.query(query_texts=[prompt], n_results=4)
    
    context_texts = []
    sources = set()
    
    if results["documents"] and results["documents"][0]:
        context_texts = results["documents"][0]
        metadatas = results["metadatas"][0]
        for m in metadatas:
            if m and "source" in m:
                sources.add(Path(m["source"]).name)
                
    context_str = "\n\n---\n\n".join(context_texts)
    
    sys_prompt = f"""Du bist ein hilfreicher KI-Assistent. Beantworte die Frage basierend auf dem folgenden Kontext. Wenn die Antwort nicht im Kontext steht, sage einfach, dass du es nicht weisst.
    
KONTEXT:
{context_str}

FRAGE: {prompt}"""

    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/api/generate",
            json={
                "model": model,
                "prompt": sys_prompt,
                "stream": False,
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        
        # Replace newlines with <br> for HTML rendering
        html_response = data.get("response", "").replace("\n", "<br>")
        
        return {
            "response": html_response,
            "sources": list(sources)
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
