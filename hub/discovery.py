from __future__ import annotations
import asyncio, ipaddress
from urllib.parse import urlsplit
import httpx
from .settings import load_json,settings
DEFINITIONS=load_json("config/services.json")
def validate_network(value:str):
    network=ipaddress.ip_network(value,strict=False)
    if network.version!=4 or network.num_addresses>256: raise ValueError("Discovery is limited to IPv4 /24 networks or smaller.")
    if not any(network.subnet_of(ipaddress.ip_network(x)) for x in settings.discovery_networks): raise ValueError("Network is outside configured private discovery ranges.")
    return network
def validate_base_url(value:str)->str:
    parsed=urlsplit(value)
    if parsed.scheme not in {"http","https"} or not parsed.hostname: raise ValueError("Only HTTP(S) service URLs are supported.")
    host=parsed.hostname
    try:
        ip=ipaddress.ip_address(host)
        if not (ip.is_private or ip.is_loopback or ip in ipaddress.ip_network("100.64.0.0/10")): raise ValueError("Public addresses are disabled.")
    except ValueError as exc:
        if "Public addresses" in str(exc): raise
        if not (host.endswith(".local") or host in {"localhost","host.docker.internal"}): raise ValueError("Host must be private, localhost, or mDNS.")
    return value.rstrip("/")
async def _probe(client,host,definition):
    base=f"http://{host}:{definition['default_port']}"
    try:
        response=await client.get(base+definition["health_path"])
        if response.status_code>=500:return None
        return {"name":definition["id"],"kind":definition["kind"],"base_url":base,"status_code":response.status_code,"verified":response.status_code<400}
    except (httpx.HTTPError,ValueError): return None
async def scan(network_value:str)->list[dict]:
    network=validate_network(network_value); semaphore=asyncio.Semaphore(64)
    async with httpx.AsyncClient(timeout=.7,follow_redirects=False) as client:
        async def limited(host,definition):
            async with semaphore:return await _probe(client,host,definition)
        found=await asyncio.gather(*(limited(str(h),d) for h in network.hosts() for d in DEFINITIONS))
    return list({(x["kind"],x["base_url"]):x for x in found if x}.values())
