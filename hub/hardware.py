from __future__ import annotations
import json, os, platform, subprocess
from typing import Any
def _run(cmd:list[str],timeout:int=8)->str:
    return subprocess.check_output(cmd,text=True,stderr=subprocess.STDOUT,timeout=timeout).strip()
def _nvidia()->list[dict[str,Any]]:
    try: out=_run(["nvidia-smi","--query-gpu=index,uuid,name,memory.total,driver_version","--format=csv,noheader,nounits"])
    except Exception: return []
    result=[]
    for line in out.splitlines():
        p=[x.strip() for x in line.split(",")]
        if len(p)==5: result.append({"id":p[1],"vendor":"nvidia","index":int(p[0]),"name":p[2],"memory_mib":int(p[3]),"driver":p[4],"backend":"cuda"})
    return result
def _apple()->list[dict[str,Any]]:
    if platform.system()!="Darwin": return []
    try:
        raw=json.loads(_run(["system_profiler","SPHardwareDataType","-json"],15))
        item=raw.get("SPHardwareDataType",[{}])[0]; chip=item.get("chip_type") or item.get("machine_name") or "Apple Silicon"
        mem=int(_run(["sysctl","-n","hw.memsize"]))//1024//1024
        if "Apple" in chip or platform.machine()=="arm64": return [{"id":"apple-metal-0","vendor":"apple","index":0,"name":chip,"memory_mib":mem,"backend":"metal","unified_memory":True}]
    except Exception: pass
    return []
def _amd()->list[dict[str,Any]]:
    try: data=json.loads(_run(["rocm-smi","--showproductname","--showmeminfo","vram","--json"],12))
    except Exception: return []
    result=[]
    for key,value in data.items():
        if not isinstance(value,dict): continue
        total=next((v for k,v in value.items() if "Total Memory" in k),0)
        result.append({"id":f"amd-{key}","vendor":"amd","index":len(result),"name":value.get("Card series") or value.get("Card model") or key,"memory_mib":int(total)//1024//1024 if total else 0,"backend":"rocm"})
    return result
def recommend(devices:list[dict[str,Any]])->dict[str,Any]:
    if not devices: return {"topology":"cpu","reason":"No supported accelerator detected."}
    if len(devices)==1: return {"topology":"single","reason":"Use one serialized accelerator queue.","placements":[{"accelerator_id":devices[0]["id"],"roles":["chat","vision","audio","image"]}]}
    same=len({(d["vendor"],d.get("memory_mib",0)) for d in devices})==1
    if same: return {"topology":"per-device","reason":"Use one provider instance per GPU for throughput; pool only oversized models.","pooling_candidate":True}
    ordered=sorted(devices,key=lambda d:d.get("memory_mib",0),reverse=True)
    return {"topology":"heterogeneous","reason":"Use independent workers and put large models on the largest device.","placements":[{"accelerator_id":d["id"],"roles":["large-models","image"] if i==0 else ["whisper","embeddings","batch"]} for i,d in enumerate(ordered)]}
def inventory()->dict[str,Any]:
    accelerators=_nvidia()+_amd()+_apple()
    return {"host":platform.node(),"system":platform.system(),"release":platform.release(),"machine":platform.machine(),"cpu_count":os.cpu_count(),"accelerators":accelerators,"recommendation":recommend(accelerators)}
