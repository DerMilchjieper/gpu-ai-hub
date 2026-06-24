from __future__ import annotations
import asyncio,os,platform,socket
import httpx
from .hardware import inventory
async def main():
    control=os.environ["HUB_CONTROL_URL"].rstrip("/")
    token=os.environ["HUB_WORKER_TOKEN"];worker_id=os.getenv("HUB_WORKER_ID",socket.gethostname())
    ollama=os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434").rstrip("/")
    headers={"Authorization":"Bearer "+token}
    async with httpx.AsyncClient(timeout=330) as client:
        while True:
            heartbeat={"id":worker_id,"name":socket.gethostname(),"platform":platform.platform(),"capabilities":inventory()}
            try:
                await client.post(control+"/api/workers/heartbeat",json=heartbeat,headers=headers)
                claim=await client.post(f"{control}/api/workers/{worker_id}/jobs/claim",headers=headers)
                if claim.status_code==204:
                    await asyncio.sleep(2);continue
                claim.raise_for_status();job=claim.json()
                try:
                    if job["kind"]!="ollama.generate":raise RuntimeError("Worker supports ollama.generate only.")
                    payload=job["payload"]
                    response=await client.post(ollama+"/api/generate",json={"model":payload["model"],"prompt":payload["prompt"],"stream":False})
                    response.raise_for_status();data=response.json();summary=(data.get("response") or data.get("thinking") or "")[:500]
                    result={"ok":True,"summary":summary}
                except Exception as exc:result={"ok":False,"error":str(exc)}
                await client.post(f"{control}/api/workers/{worker_id}/jobs/{job['id']}/complete",json=result,headers=headers)
            except httpx.HTTPError as exc:
                print(f"worker cycle failed: {exc}",flush=True);await asyncio.sleep(5)
if __name__=="__main__":asyncio.run(main())
