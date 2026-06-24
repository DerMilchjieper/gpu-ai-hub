from __future__ import annotations
import socket
from zeroconf import ServiceInfo,Zeroconf
def register(address:str,hostname:str,port:int=80):
    if not address:return None
    try:
        info=ServiceInfo("_http._tcp.local.",f"GPU AI Hub._http._tcp.local.",addresses=[socket.inet_aton(address)],port=port,properties={"path":"/"},server=hostname.rstrip(".")+".")
        zc=Zeroconf();zc.register_service(info)
        return zc,info
    except Exception as exc:
        print(f"mDNS registration unavailable: {exc}",flush=True);return None
def unregister(handle):
    if not handle:return
    zc,info=handle
    try:zc.unregister_service(info)
    finally:zc.close()
