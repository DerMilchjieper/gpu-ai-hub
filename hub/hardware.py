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
def _system_memory_mib()->int:
    try:
        if hasattr(os,"sysconf"):
            return int(os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES")//1024//1024)
    except Exception: pass
    try:
        if platform.system()=="Darwin": return int(_run(["sysctl","-n","hw.memsize"]))//1024//1024
    except Exception: pass
    return 0
def recommend(devices:list[dict[str,Any]])->dict[str,Any]:
    if not devices: return {"topology":"cpu","reason":"No supported accelerator detected."}
    if len(devices)==1: return {"topology":"single","reason":"Use one serialized accelerator queue.","placements":[{"accelerator_id":devices[0]["id"],"roles":["chat","vision","audio","image"]}]}
    same=len({(d["vendor"],d.get("memory_mib",0)) for d in devices})==1
    if same: return {"topology":"per-device","reason":"Use one provider instance per GPU for throughput; pool only oversized models.","pooling_candidate":True}
    ordered=sorted(devices,key=lambda d:d.get("memory_mib",0),reverse=True)
    return {"topology":"heterogeneous","reason":"Use independent workers and put large models on the largest device.","placements":[{"accelerator_id":d["id"],"roles":["large-models","image"] if i==0 else ["whisper","embeddings","batch"]} for i,d in enumerate(ordered)]}
def inventory()->dict[str,Any]:
    accelerators=_nvidia()+_amd()+_apple()
    return {"host":platform.node(),"system":platform.system(),"release":platform.release(),"machine":platform.machine(),"cpu_count":os.cpu_count(),"memory_mib":_system_memory_mib(),"accelerators":accelerators,"recommendation":recommend(accelerators)}
def model_recommendations(inv:dict[str,Any],profiles:dict[str,list[dict[str,Any]]])->dict[str,Any]:
    accelerators=inv.get("accelerators",[])
    if accelerators:
        best=max(accelerators,key=lambda item:item.get("memory_mib",0))
        memory_gib=best.get("memory_mib",0)/1024
        backend=best.get("backend") or best.get("vendor") or "accelerator"
        device={"kind":best.get("vendor","gpu"),"name":best.get("name","GPU"),"backend":backend,"memory_gib":round(memory_gib,1),"unified_memory":bool(best.get("unified_memory"))}
        available_gib=memory_gib*.65 if best.get("unified_memory") else memory_gib
    else:
        memory_gib=inv.get("memory_mib",0)/1024
        available_gib=max(0,memory_gib*.5)
        device={"kind":"cpu","name":f"CPU only, {inv.get('cpu_count') or '?'} threads","backend":"cpu","memory_gib":round(memory_gib,1),"unified_memory":False}
    profile_order=["cpu","minimal","recommended","large"]
    fitting=[]
    for name in profile_order:
        models=profiles.get(name,[])
        if models and all(float(model.get("min_memory_gib",0))<=available_gib for model in models):
            fitting.append(name)
    selected=fitting[-1] if fitting else "cpu" if profiles.get("cpu") else "minimal"
    selected_models=profiles.get(selected,[])
    alternatives=[]
    for name in profile_order:
        models=profiles.get(name,[])
        if not models: continue
        required=max(float(model.get("min_memory_gib",0)) for model in models)
        alternatives.append({"profile":name,"fits":required<=available_gib,"required_gib":required,"models":models})
    if device["kind"]=="cpu":
        reason="No supported GPU was detected. Use the CPU starter profile and prefer small models."
    elif device.get("unified_memory"):
        reason="Apple Silicon uses unified memory; the recommendation keeps headroom for macOS and ComfyUI."
    else:
        reason=f"Largest detected accelerator has about {device['memory_gib']} GiB VRAM; selected the largest profile that fits with headroom."
    return {"device":device,"available_gib":round(available_gib,1),"selected_profile":selected,"models":selected_models,"alternatives":alternatives,"pull_command":f"scripts/pull-models.sh {selected}","windows_pull_command":f".\\scripts\\pull-models.ps1 {selected}","reason":reason}
