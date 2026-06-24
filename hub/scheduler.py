from __future__ import annotations
import asyncio,json,time
from .db import connect
from .providers import generate
class Scheduler:
    def __init__(self): self.running=True;self.task=None
    async def start(self): self.task=asyncio.create_task(self.loop())
    async def stop(self):
        self.running=False
        if self.task: self.task.cancel()
    async def loop(self):
        while self.running:
            job=None
            with connect() as conn:
                row=conn.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY priority DESC,created_at LIMIT 1").fetchone()
                if row:
                    job=dict(row);now=time.time()
                    conn.execute("UPDATE jobs SET status='running',started_at=?,lease_until=? WHERE id=? AND status='queued'",(now,now+330,job["id"]))
            if not job:
                await asyncio.sleep(.5);continue
            await self.execute(job)
    async def execute(self,job):
        try:
            payload=json.loads(job["payload"])
            if job["kind"]!="ollama.generate": raise RuntimeError("No executor for job kind.")
            result=await generate(payload["prompt"],payload["model"],job.get("service_id"))
            summary=(result.get("response") or result.get("thinking") or "")[:500]
            with connect() as conn: conn.execute("UPDATE jobs SET status='done',result_summary=?,finished_at=?,lease_until=NULL WHERE id=?",(summary,time.time(),job["id"]))
        except Exception as exc:
            with connect() as conn: conn.execute("UPDATE jobs SET status='error',error=?,finished_at=?,lease_until=NULL WHERE id=?",(str(exc)[:1000],time.time(),job["id"]))
scheduler=Scheduler()
