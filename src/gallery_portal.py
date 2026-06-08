import json
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

GALLERY_ROOT = Path("/home/wizzard/ai/gallery")
DATA_DIR = GALLERY_ROOT / "data"
ALBUMS_FILE = DATA_DIR / "albums.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Central locations for AI media
MEDIA_SOURCES = {
    "images": Path("/home/wizzard/ai/comfy_output"),
    "voice": Path("/home/wizzard/ai/tts/outputs"),
    "music": Path("/home/wizzard/ai/audio_gen/outputs"),
    "video": Path("/home/wizzard/ai/video/outputs"),
    "texts": Path("/home/wizzard/transcripts")
}

# Ensure all exists
for p in MEDIA_SOURCES.values():
    p.mkdir(parents=True, exist_ok=True)

# Mount sources for serving
for key, path in MEDIA_SOURCES.items():
    app.mount(f"/media/{key}", StaticFiles(directory=str(path)), name=key)

def load_albums():
    if not ALBUMS_FILE.exists(): return {}
    try:
        with open(ALBUMS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_albums(albums):
    with open(ALBUMS_FILE, "w") as f: json.dump(albums, f, indent=2)

HTML = r'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zen Gallery</title>
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
    
    .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; margin-top: 24px; }
    .media-card { position: relative; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); overflow: hidden; transition: transform 0.2s; }
    .media-card:hover { transform: translateY(-4px); border-color: var(--brand); }
    .media-preview { width: 100%; aspect-ratio: 16/9; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .media-preview img, .media-preview video { width: 100%; height: 100%; object-fit: cover; }
    .media-info { padding: 12px; font-size: 13px; }
    .media-name { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .media-meta { color: var(--muted); margin-top: 4px; font-size: 11px; }
    
    .media-actions { position: absolute; top: 8px; right: 8px; display: flex; gap: 6px; opacity: 0; transition: opacity 0.2s; }
    .media-card:hover .media-actions { opacity: 1; }
    .btn-icon { width: 32px; height: 32px; border-radius: 6px; background: rgba(0,0,0,0.7); border: 1px solid var(--line); color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; }
    .btn-icon:hover { background: var(--danger); }
    .btn-icon.add-album:hover { background: var(--brand); }

    .sidebar { display: grid; gap: 14px; align-content: start; }
    .main-content { display: block; }
    .layout { display: grid; grid-template-columns: 240px 1fr; gap: 24px; }
    
    .album-item { padding: 10px 12px; border-radius: 8px; cursor: pointer; background: rgba(255,255,255,0.03); border: 1px solid transparent; transition: 0.2s; }
    .album-item:hover, .album-item.active { background: rgba(85,214,189,0.1); border-color: var(--line); color: var(--brand); }
    
    .filter-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
    .badge { padding: 6px 12px; border-radius: 99px; background: rgba(255,255,255,0.05); cursor: pointer; font-size: 12px; font-weight: 700; border: 1px solid var(--line); }
    .badge.active { background: var(--brand); color: #000; border-color: transparent; }
    
    @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } .sidebar { order: 2; } }
  </style>
</head>
<body data-page="gallery">
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
    <div class="layout">
        <aside class="sidebar">
            <section class="panel" style="padding:16px;">
                <div class="label" style="margin-bottom:12px;">Alben</div>
                <div id="albumsList">
                    <div class="album-item active" data-id="all">Alle Medien</div>
                </div>
                <button class="badge" style="margin-top:12px; width:100%;" onclick="createAlbum()">+ Neues Album</button>
            </section>
            
            <section class="panel" style="padding:16px;">
                <div class="label" style="margin-bottom:12px;">Speicherplatz</div>
                <div id="diskUsage" style="font-size:14px; font-weight:800;">-</div>
            </section>
        </aside>

        <section class="main-content">
            <header>
                <div class="hero">
                    <div class="eyebrow">Zen Gallery</div>
                    <h1 style="margin:8px 0;">Medien Verwaltung.</h1>
                    <p>Zentraler Zugriff auf alle KI-generierten Bilder, Stimmen und Videos. Mit Loeschfunktion und Alben.</p>
                </div>
            </header>

            <div class="filter-bar">
                <div class="badge active" data-type="all">Alle</div>
                <div class="badge" data-type="images">Bilder</div>
                <div class="badge" data-type="video">Videos</div>
                <div class="badge" data-type="music">Musik</div>
                <div class="badge" data-type="voice">Stimmen</div>
                <div class="badge" data-type="texts">Transkripte</div>
            </div>

            <div class="gallery-grid" id="galleryGrid">
                <!-- Media Cards will appear here -->
            </div>
        </section>
    </div>
  </main>

  <script>
    let currentType = 'all';
    let currentAlbum = 'all';
    let allMedia = [];

    async function loadMedia() {
        try {
            const res = await fetch(`/api/media?type=${currentType}&album=${currentAlbum}`);
            const data = await res.json();
            allMedia = data.files;
            renderGallery();
            document.getElementById('diskUsage').textContent = data.disk_usage;
        } catch(e) { console.error(e); }
    }

    function renderGallery() {
        const grid = document.getElementById('galleryGrid');
        grid.innerHTML = allMedia.map(m => {
            let preview = '';
            if(m.category === 'images') preview = `<img src="/media/images/${m.name}" loading="lazy">`;
            else if(m.category === 'video') preview = `<video src="/media/video/${m.name}" muted onmouseover="this.play()" onmouseout="this.pause()"></video>`;
            else if(m.category === 'voice') preview = `<div style="font-size:32px;">🔊</div>`;
            else if(m.category === 'music') preview = `<div style="font-size:32px;">🎵</div>`;
            else preview = `<div style="font-size:32px;">📄</div>`;

            return `
                <div class="media-card" data-path="${m.category}/${m.name}">
                    <div class="media-preview">${preview}</div>
                    <div class="media-actions">
                        <button class="btn-icon add-album" title="Zum Album hinzufügen" onclick="addToAlbum('${m.category}','${m.name}')">📁</button>
                        <button class="btn-icon" title="Löschen" onclick="deleteFile('${m.category}','${m.name}')">🗑️</button>
                    </div>
                    <div class="media-info">
                        <div class="media-name">${m.name}</div>
                        <div class="media-meta">${m.size} • ${m.date}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async function deleteFile(cat, name) {
        if(!confirm(`Datei ${name} wirklich unwiderruflich loeschen?`)) return;
        try {
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ category: cat, name: name })
            });
            if(res.ok) loadMedia();
        } catch(e) { alert("Fehler beim Loeschen"); }
    }

    async function createAlbum() {
        const name = prompt("Name des neuen Albums:");
        if(!name) return;
        await fetch('/api/albums', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        loadAlbums();
    }

    async function loadAlbums() {
        const res = await fetch('/api/albums');
        const albums = await res.json();
        const list = document.getElementById('albumsList');
        list.innerHTML = `<div class="album-item ${currentAlbum==='all'?'active':''}" onclick="selectAlbum('all')">Alle Medien</div>`;
        Object.keys(albums).forEach(id => {
            list.innerHTML += `<div class="album-item ${currentAlbum===id?'active':''}" onclick="selectAlbum('${id}')">${albums[id].name}</div>`;
        });
    }

    function selectAlbum(id) {
        currentAlbum = id;
        loadAlbums();
        loadMedia();
    }

    document.querySelectorAll('.filter-bar .badge').forEach(b => {
        b.onclick = () => {
            document.querySelectorAll('.filter-bar .badge').forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            currentType = b.dataset.type;
            loadMedia();
        };
    });

    loadMedia();
    loadAlbums();
  </script>
</body>
</html>'''

@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return HTML

@app.get('/api/media')
def list_media(type: str = "all", album: str = "all"):
    files = []
    albums = load_albums()
    
    categories = [type] if type != "all" else MEDIA_SOURCES.keys()
    
    for cat in categories:
        path = MEDIA_SOURCES[cat]
        for f in sorted(path.glob("*"), key=os.path.getmtime, reverse=True):
            if f.is_file() and not f.name.startswith("."):
                # If filtered by album
                if album != "all":
                    if f.name not in albums.get(album, {}).get("files", []):
                        continue
                
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "category": cat,
                    "size": f"{stat.st_size / (1024*1024):.1f} MB",
                    "date": time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
                })
    
    # Simple disk usage check
    du = shutil.disk_usage("/home/wizzard")
    usage_str = f"{du.used / (1024**3):.1f} / {du.total / (1024**3):.1f} GB belegt"
    
    return {"files": files, "disk_usage": usage_str}

@app.post('/api/delete')
def delete_media(payload: dict = Body(...)):
    cat = payload.get("category")
    name = payload.get("name")
    if cat not in MEDIA_SOURCES: raise HTTPException(status_code=400)
    
    file_path = MEDIA_SOURCES[cat] / name
    if file_path.exists():
        file_path.unlink()
        return {"status": "ok"}
    raise HTTPException(status_code=404)

@app.get('/api/albums')
def get_albums():
    return load_albums()

@app.post('/api/albums')
def create_album(payload: dict = Body(...)):
    name = payload.get("name")
    albums = load_albums()
    album_id = "".join(c if c.isalnum() else "_" for c in name.lower())
    albums[album_id] = {"name": name, "files": []}
    save_albums(albums)
    return {"status": "ok", "id": album_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
