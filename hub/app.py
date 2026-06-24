from __future__ import annotations
import hashlib,json,secrets,time,uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import Body,Depends,FastAPI,HTTPException,Request,Response
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from . import discovery,hardware,mdns,providers
from .db import connect,initialize,password_ok,rows
from .scheduler import scheduler
from .settings import ROOT,load_json,settings,translations

STATIC=ROOT/"hub"/"static"

class Login(BaseModel):
    username:str;password:str
class ServiceInput(BaseModel):
    name:str=Field(min_length=1,max_length=80);kind:str=Field(min_length=1,max_length=32);base_url:str;accelerator_id:str|None=None;max_parallel:int=Field(default=1,ge=1,le=32)
class ChatInput(BaseModel):
    prompt:str=Field(min_length=1,max_length=100000);model:str=Field(min_length=1,max_length=160);service_id:int|None=None
class CompareInput(BaseModel):
    prompt:str=Field(min_length=1,max_length=100000);targets:list[dict]=Field(min_length=1,max_length=8)
class NoteInput(BaseModel):
    title:str=Field(min_length=1,max_length=200);body:str=Field(default="",max_length=1000000)
class TaskInput(BaseModel):
    title:str=Field(min_length=1,max_length=200);detail:str=Field(default="",max_length=100000);status:str="open";due_at:float|None=None
class EventInput(BaseModel):
    title:str=Field(min_length=1,max_length=200);detail:str=Field(default="",max_length=100000);starts_at:float;ends_at:float|None=None
class JobInput(BaseModel):
    kind:str="ollama.generate";mode:str="auto";payload:dict;requirements:dict=Field(default_factory=dict);service_id:int|None=None;priority:int=Field(default=0,ge=-100,le=100)

def token_hash(value:str)->str:return hashlib.sha256(value.encode()).hexdigest()
def current_session(request:Request)->dict:
    token=request.cookies.get("hub_session")
    if not token: raise HTTPException(401,"Authentication required.")
    found=rows("""SELECT sessions.csrf_token,sessions.expires_at,users.id user_id,users.username,users.is_admin FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token_hash=?""",(token_hash(token),))
    if not found or found[0]["expires_at"]<time.time(): raise HTTPException(401,"Session expired.")
    return found[0]
def admin(session:dict=Depends(current_session))->dict:
    if not session["is_admin"]:raise HTTPException(403,"Admin access required.")
    return session
def csrf(request:Request,session:dict=Depends(current_session))->dict:
    if not secrets.compare_digest(request.headers.get("X-CSRF-Token",""),session["csrf_token"]):raise HTTPException(403,"Invalid CSRF token.")
    return session
def admin_csrf(session:dict=Depends(csrf))->dict:
    if not session["is_admin"]:raise HTTPException(403,"Admin access required.")
    return session

@asynccontextmanager
async def lifespan(app:FastAPI):
    generated=initialize()
    if generated: print(f"GPU AI Hub initial admin: {settings.admin_user} / {generated}",flush=True)
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM services WHERE kind='ollama' LIMIT 1").fetchone():
            conn.execute("INSERT INTO services(name,kind,base_url,created_at) VALUES(?,?,?,?)",("Default Ollama","ollama",settings.ollama_base_url,time.time()))
    await scheduler.start()
    mdns_handle=mdns.register(settings.mdns_address,settings.hostname)
    yield
    mdns.unregister(mdns_handle)
    await scheduler.stop()

app=FastAPI(title="GPU AI Hub",version="0.2.0-alpha.1",lifespan=lifespan)

@app.middleware("http")
async def security_headers(request:Request,call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff";response.headers["Referrer-Policy"]="no-referrer"
    response.headers["X-Frame-Options"]="DENY";response.headers["Content-Security-Policy"]="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"
    return response

@app.get("/")
def index():return FileResponse(STATIC/"index.html")
@app.get("/app.js")
def js():return FileResponse(STATIC/"app.js",media_type="text/javascript")
@app.get("/styles.css")
def css():return FileResponse(STATIC/"styles.css",media_type="text/css")
@app.get("/healthz")
def health():return {"status":"ok","version":"0.2.0-alpha.1"}

@app.get("/api/bootstrap")
def bootstrap(request:Request,locale:str="en"):
    try:s=current_session(request);user={"username":s["username"],"is_admin":bool(s["is_admin"]),"csrf_token":s["csrf_token"]}
    except HTTPException:user=None
    return {"hostname":settings.hostname,"locale":locale,"translations":translations(locale),"user":user}

@app.post("/api/auth/login")
def login(payload:Login,response:Response):
    with connect() as conn:
        user=conn.execute("SELECT * FROM users WHERE username=?",(payload.username,)).fetchone()
        if not user or not password_ok(payload.password,user["password_hash"]):raise HTTPException(401,"Invalid credentials.")
        token=secrets.token_urlsafe(32);csrf_token=secrets.token_urlsafe(24);expires=time.time()+settings.session_ttl_hours*3600
        conn.execute("DELETE FROM sessions WHERE expires_at<?",(time.time(),))
        conn.execute("INSERT INTO sessions(token_hash,user_id,csrf_token,expires_at) VALUES(?,?,?,?)",(token_hash(token),user["id"],csrf_token,expires))
    response.set_cookie("hub_session",token,httponly=True,samesite="strict",max_age=settings.session_ttl_hours*3600)
    return {"username":user["username"],"is_admin":bool(user["is_admin"]),"csrf_token":csrf_token}
@app.post("/api/auth/logout")
def logout(response:Response,request:Request,_=Depends(csrf)):
    token=request.cookies.get("hub_session")
    with connect() as conn:conn.execute("DELETE FROM sessions WHERE token_hash=?",(token_hash(token),))
    response.delete_cookie("hub_session");return {"status":"ok"}

@app.get("/api/dashboard")
def dashboard(_=Depends(current_session)):
    return {"hardware":hardware.inventory(),"services":rows("SELECT id,name,kind,base_url,verified,last_status,last_seen,accelerator_id,max_parallel FROM services WHERE enabled=1 ORDER BY kind,name"),"jobs":rows("SELECT id,kind,mode,status,service_id,worker_id,priority,result_summary,error,created_at,started_at,finished_at FROM jobs ORDER BY created_at DESC LIMIT 25")}
@app.get("/api/hardware")
def get_hardware(_=Depends(current_session)):return hardware.inventory()
@app.get("/api/models")
def models(_=Depends(current_session)):return load_json("config/models.json")
@app.get("/api/services")
def services(_=Depends(current_session)):return rows("SELECT * FROM services ORDER BY kind,name")
@app.post("/api/services")
def add_service(payload:ServiceInput,_=Depends(csrf)):
    base=discovery.validate_base_url(payload.base_url)
    with connect() as conn:
        cur=conn.execute("INSERT INTO services(name,kind,base_url,accelerator_id,max_parallel,created_at) VALUES(?,?,?,?,?,?)",(payload.name,payload.kind,base,payload.accelerator_id,payload.max_parallel,time.time()))
        return {"id":cur.lastrowid}
@app.delete("/api/services/{service_id}")
def delete_service(service_id:int,_=Depends(csrf)):
    with connect() as conn:conn.execute("DELETE FROM services WHERE id=?",(service_id,))
    return {"status":"ok"}
@app.post("/api/discovery/scan")
async def scan(network:str=Body(embed=True),_=Depends(admin_csrf)):return await discovery.scan(network)
@app.post("/api/services/health")
async def service_health(_=Depends(current_session)):
    current=rows("SELECT * FROM services WHERE enabled=1")
    async with httpx.AsyncClient(timeout=3,follow_redirects=False) as client:
        async def check(item):
            definition=next((x for x in load_json("config/services.json") if x["kind"]==item["kind"]),None)
            path=definition["health_path"] if definition else "/"
            try:r=await client.get(item["base_url"].rstrip("/")+path);status="online" if r.status_code<500 else "degraded"
            except httpx.HTTPError:status="offline"
            with connect() as conn:conn.execute("UPDATE services SET last_status=?,last_seen=? WHERE id=?",(status,time.time(),item["id"]))
            return {"id":item["id"],"status":status}
        return await __import__("asyncio").gather(*(check(x) for x in current))

@app.post("/api/chat")
async def chat(payload:ChatInput,_=Depends(current_session)):return await providers.generate(payload.prompt,payload.model,payload.service_id)
@app.post("/api/compare")
async def compare(payload:CompareInput,_=Depends(current_session)):return await providers.compare(payload.prompt,payload.targets)
@app.post("/api/research")
async def research(query:str=Body(embed=True),_=Depends(current_session)):return await providers.research(query)

@app.get("/api/notes")
def list_notes(_=Depends(current_session)):return rows("SELECT * FROM notes ORDER BY updated_at DESC")
@app.post("/api/notes")
def create_note(payload:NoteInput,_=Depends(csrf)):
    now=time.time()
    with connect() as conn:cur=conn.execute("INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)",(payload.title,payload.body,now,now));return {"id":cur.lastrowid}
@app.delete("/api/notes/{item_id}")
def delete_note(item_id:int,_=Depends(csrf)):
    with connect() as conn:conn.execute("DELETE FROM notes WHERE id=?",(item_id,))
    return {"status":"ok"}
@app.get("/api/tasks")
def list_tasks(_=Depends(current_session)):return rows("SELECT * FROM tasks ORDER BY status,due_at,created_at DESC")
@app.post("/api/tasks")
def create_task(payload:TaskInput,_=Depends(csrf)):
    now=time.time()
    with connect() as conn:cur=conn.execute("INSERT INTO tasks(title,detail,status,due_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",(payload.title,payload.detail,payload.status,payload.due_at,now,now));return {"id":cur.lastrowid}
@app.delete("/api/tasks/{item_id}")
def delete_task(item_id:int,_=Depends(csrf)):
    with connect() as conn:conn.execute("DELETE FROM tasks WHERE id=?",(item_id,))
    return {"status":"ok"}
@app.get("/api/events")
def list_events(_=Depends(current_session)):return rows("SELECT * FROM events ORDER BY starts_at")
@app.post("/api/events")
def create_event(payload:EventInput,_=Depends(csrf)):
    with connect() as conn:cur=conn.execute("INSERT INTO events(title,detail,starts_at,ends_at,created_at) VALUES(?,?,?,?,?)",(payload.title,payload.detail,payload.starts_at,payload.ends_at,time.time()));return {"id":cur.lastrowid}
@app.delete("/api/events/{item_id}")
def delete_event(item_id:int,_=Depends(csrf)):
    with connect() as conn:conn.execute("DELETE FROM events WHERE id=?",(item_id,))
    return {"status":"ok"}

@app.get("/api/workers")
def workers(_=Depends(current_session)):return rows("SELECT * FROM workers ORDER BY name")
def worker_authorized(request:Request):
    auth=request.headers.get("Authorization","")
    if not settings.worker_token or not secrets.compare_digest(auth,"Bearer "+settings.worker_token):raise HTTPException(401,"Invalid worker token.")
@app.post("/api/workers/heartbeat")
def worker_heartbeat(request:Request,payload:dict=Body(...)):
    worker_authorized(request)
    worker_id=str(payload.get("id",""))[:120]
    if not worker_id:raise HTTPException(400,"Worker id required.")
    with connect() as conn:
        conn.execute("""INSERT INTO workers(id,name,platform,capabilities,status,last_seen) VALUES(?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET name=excluded.name,platform=excluded.platform,capabilities=excluded.capabilities,status='online',last_seen=excluded.last_seen""",
        (worker_id,str(payload.get("name",worker_id))[:200],str(payload.get("platform","unknown"))[:500],json.dumps(payload.get("capabilities",{})),"online",time.time()))
    return {"status":"ok"}

@app.post("/api/workers/{worker_id}/jobs/claim")
def worker_claim(worker_id:str,request:Request):
    worker_authorized(request);now=time.time()
    with connect() as conn:
        conn.execute("UPDATE jobs SET status='queued_worker',worker_id=NULL,lease_until=NULL WHERE status='running_worker' AND lease_until<?",(now,))
        row=conn.execute("SELECT * FROM jobs WHERE status='queued_worker' AND (worker_id IS NULL OR worker_id=?) ORDER BY priority DESC,created_at LIMIT 1",(worker_id,)).fetchone()
        if not row:return Response(status_code=204)
        conn.execute("UPDATE jobs SET status='running_worker',worker_id=?,started_at=?,lease_until=? WHERE id=? AND status='queued_worker'",(worker_id,now,now+330,row["id"]))
        item=dict(row);item["payload"]=json.loads(item["payload"]);item["requirements"]=json.loads(item["requirements"])
        return item
@app.post("/api/workers/{worker_id}/jobs/{job_id}/complete")
def worker_complete(worker_id:str,job_id:str,request:Request,payload:dict=Body(...)):
    worker_authorized(request);status="done" if payload.get("ok") else "error"
    with connect() as conn:
        conn.execute("UPDATE jobs SET status=?,result_summary=?,error=?,finished_at=?,lease_until=NULL WHERE id=? AND worker_id=? AND status='running_worker'",(status,str(payload.get("summary",""))[:500],str(payload.get("error",""))[:1000] or None,time.time(),job_id,worker_id))
    return {"status":status}

@app.get("/api/jobs")
def jobs(_=Depends(current_session)):return rows("SELECT id,kind,mode,status,service_id,worker_id,priority,result_summary,error,created_at,started_at,finished_at FROM jobs ORDER BY created_at DESC LIMIT 100")
@app.post("/api/jobs")
def enqueue(payload:JobInput,_=Depends(csrf)):
    if payload.mode not in {"auto","sequential","parallel","broadcast","pipeline","gang"}:raise HTTPException(400,"Unsupported scheduling mode.")
    job_id=str(uuid.uuid4())
    worker_id=payload.requirements.get("worker_id");status="queued_worker" if worker_id else "queued"
    with connect() as conn:conn.execute("INSERT INTO jobs(id,kind,mode,payload,requirements,status,service_id,worker_id,priority,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(job_id,payload.kind,payload.mode,json.dumps(payload.payload),json.dumps(payload.requirements),status,payload.service_id,worker_id,payload.priority,time.time()))
    return {"id":job_id,"status":"queued"}
@app.post("/api/jobs/{job_id}/cancel")
def cancel(job_id:str,_=Depends(csrf)):
    with connect() as conn:conn.execute("UPDATE jobs SET status='cancelled',finished_at=? WHERE id=? AND status IN ('queued','queued_worker')",(time.time(),job_id))
    return {"status":"ok"}
