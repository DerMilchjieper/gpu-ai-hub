from __future__ import annotations
import json, os
from dataclasses import dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
@dataclass(frozen=True)
class Settings:
    hostname: str = os.getenv("HUB_HOSTNAME","ai-tool-hub.local")
    locale: str = os.getenv("HUB_LOCALE","en")
    admin_user: str = os.getenv("HUB_ADMIN_USER","admin")
    admin_password: str = os.getenv("HUB_ADMIN_PASSWORD","")
    data_dir: Path = Path(os.getenv("HUB_DATA_DIR",str(ROOT/"data")))
    session_ttl_hours: int = int(os.getenv("HUB_SESSION_TTL_HOURS","24"))
    discovery_networks: tuple[str,...] = tuple(x.strip() for x in os.getenv("HUB_DISCOVERY_NETWORKS","192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,100.64.0.0/10").split(",") if x.strip())
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL","http://host.docker.internal:11434")
    searxng_base_url: str = os.getenv("SEARXNG_BASE_URL","")
    comfyui_base_url: str = os.getenv("COMFYUI_BASE_URL","http://comfyui:8188")
    whisper_base_url: str = os.getenv("WHISPER_BASE_URL","http://whisper:8001")
    n8n_base_url: str = os.getenv("N8N_BASE_URL","http://n8n:5678")
    worker_token: str = os.getenv("HUB_WORKER_TOKEN","")
    mdns_address: str = os.getenv("HUB_MDNS_ADDRESS","")
settings=Settings()
settings.data_dir.mkdir(parents=True,exist_ok=True)
def load_json(relative:str):
    return json.loads((ROOT/relative).read_text(encoding="utf-8"))
def translations(locale:str)->dict[str,str]:
    safe=locale if locale in {"de","en"} else settings.locale
    path=ROOT/"locales"/f"{safe}.json"
    if not path.exists(): path=ROOT/"locales"/"en.json"
    return json.loads(path.read_text(encoding="utf-8"))
