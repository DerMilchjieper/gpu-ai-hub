from __future__ import annotations
import os,tempfile
from pathlib import Path
from fastapi import FastAPI,File,UploadFile
from faster_whisper import WhisperModel
app=FastAPI(title="GPU AI Hub Whisper")
model=None
def get_model():
    global model
    if model is None:model=WhisperModel(os.getenv("WHISPER_MODEL","small"),device=os.getenv("WHISPER_DEVICE","cpu"),compute_type=os.getenv("WHISPER_COMPUTE_TYPE","int8"))
    return model
@app.get("/api/status")
def status():return {"status":"online","model":os.getenv("WHISPER_MODEL","small"),"loaded":model is not None}
@app.post("/api/deactivate")
def deactivate():
    global model
    model=None
    return {"status":"ok"}
@app.post("/api/transcribe")
async def transcribe(file:UploadFile=File(...),language:str|None=None):
    suffix=Path(file.filename or "audio").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tmp:
        tmp.write(await file.read());path=tmp.name
    try:
        segments,info=get_model().transcribe(path,language=language)
        return {"text":" ".join(x.text.strip() for x in segments),"language":info.language}
    finally:Path(path).unlink(missing_ok=True)
