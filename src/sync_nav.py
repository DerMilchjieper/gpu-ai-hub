import os
import re

nav_html = """      <nav class="site-nav" aria-label="Zen AI Hub Navigation">
        <a data-nav="hub" href="http://192.168.2.41:8191/">Hub</a>
        <a data-nav="gallery" href="http://192.168.2.41:8009/">Gallery</a>
        <a data-nav="avatar" href="http://192.168.2.41:8013/">Avatar Live</a>
        <a data-nav="voice_live" href="http://192.168.2.41:8015/">Voice Live</a>
        <a data-nav="prompt" href="http://192.168.2.41:8012/">Prompt Expert</a>
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
      </nav>"""

urls_js = "const urls = { hub: `http://${host}:8191/`, gallery: `http://${host}:8009/`, audio: `http://${host}:8010/`, system: `http://${host}:8008/`, queue: `http://${host}:11435/status`, vision: `http://${host}:8003/`, voice: `http://${host}:8002/`, docs: `http://${host}:8004/`, video: `http://${host}:8005/`, coder: `http://${host}:8006/`, auto: `http://${host}:8007/`, prompt: `http://${host}:8012/`, avatar: `http://${host}:8013/`, voice_live: `http://${host}:8015/`, n8n: `http://${host}:5678/`, whisper: `http://${host}:8000/`, workspace: `http://${host}:8001/?workspace=1`, comfy: `http://${host}:8188/` };"

files_to_update = [
    "/home/wizzard/api.py",
    "/home/wizzard/whisper_portal.py",
    "/home/wizzard/gpu-ai-hub/src/vision_portal.py",
    "/home/wizzard/gpu-ai-hub/src/docs_portal.py",
    "/home/wizzard/gpu-ai-hub/src/video_portal.py",
    "/home/wizzard/gpu-ai-hub/src/coder_portal.py",
    "/home/wizzard/gpu-ai-hub/src/auto_portal.py",
    "/home/wizzard/gpu-ai-hub/src/system_portal.py",
    "/home/wizzard/gpu-ai-hub/src/gallery_portal.py",
    "/home/wizzard/ai/tts/xtts/xtts_portal.py",
    "/home/wizzard/gpu-ai-hub/src/audio_portal.py",
    "/home/wizzard/gpu-ai-hub/src/prompt_portal.py",
    "/home/wizzard/gpu-ai-hub/src/avatar_portal.py"
]

for file_path in files_to_update:
    if not os.path.exists(file_path): continue
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '<nav class="site-nav"' in content:
            content = re.sub(r'<nav class="site-nav".*?</nav>', nav_html, content, flags=re.DOTALL)
            
        if 'const urls = {' in content:
            content = re.sub(r'const urls = \{.*?\};', urls_js, content, flags=re.DOTALL)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
