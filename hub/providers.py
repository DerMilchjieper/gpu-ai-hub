from __future__ import annotations
import asyncio
from typing import Any
import httpx
from .db import rows
from .settings import settings
def service(service_id:int|None=None,kind:str="ollama")->dict:
    if service_id is not None:
        found=rows("SELECT * FROM services WHERE id=? AND enabled=1",(service_id,))
    else:
        found=rows("SELECT * FROM services WHERE kind=? AND enabled=1 ORDER BY verified DESC,id",(kind,))
    if not found and kind=="ollama": return {"id":None,"base_url":settings.ollama_base_url,"kind":"ollama","name":"Default Ollama"}
    if not found: raise RuntimeError(f"No enabled {kind} service.")
    return found[0]
async def generate(prompt:str,model:str,service_id:int|None=None)->dict[str,Any]:
    target=service(service_id,"ollama")
    async with httpx.AsyncClient(timeout=300) as client:
        response=await client.post(target["base_url"].rstrip("/")+"/api/generate",json={"model":model,"prompt":prompt,"stream":False})
        response.raise_for_status();data=response.json()
    return {"service_id":target.get("id"),"service":target.get("name"),"model":model,"response":data.get("response",""),"thinking":data.get("thinking","")}
async def compare(prompt:str,model_service_pairs:list[dict])->list[dict]:
    async def one(item):
        try:return await generate(prompt,item["model"],item.get("service_id"))
        except Exception as exc:return {"model":item.get("model"),"error":str(exc)}
    return await asyncio.gather(*(one(item) for item in model_service_pairs))
async def research(query:str)->dict:
    if not settings.searxng_base_url: raise RuntimeError("SEARXNG_BASE_URL is not configured.")
    async with httpx.AsyncClient(timeout=30) as client:
        response=await client.get(settings.searxng_base_url.rstrip("/")+"/search",params={"q":query,"format":"json"})
        response.raise_for_status();data=response.json()
    return {"query":query,"results":[{"title":x.get("title"),"url":x.get("url"),"content":x.get("content")} for x in data.get("results",[])[:10]]}
