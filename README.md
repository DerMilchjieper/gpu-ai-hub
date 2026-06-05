# GPU AI Hub

Local GPU-first orchestration for Ollama, Whisper and ComfyUI on a single NVIDIA GPU workstation.

The project provides:

- a FIFO HTTP gateway for GPU AI jobs
- hard GPU-only policy for queued requests
- active VRAM release between Ollama, Whisper and ComfyUI
- a browser landing page for GPU queue status, manual offload, Ollama tests, Whisper and ComfyUI workflow links
- a user-level systemd service template

## Ports

Default local layout:

| Service | Direct Port | Queued Route |
| --- | ---: | --- |
| GPU Orchestrator | `11435` | `http://HOST:11435/status` dashboard, `http://HOST:11435/api/status` JSON |
| Ollama | `11434` | `http://HOST:11435/api/generate` and `/api/chat` |
| Whisper | `8001` | `http://HOST:11435/whisper/api/...` |
| ComfyUI | `8188` | `http://HOST:11435/comfy/...` for HTTP API clients |
| Landing Page | `8191` | static browser hub |

ComfyUI's browser UI still opens direct port `8188` because it uses WebSockets. API clients that submit ComfyUI prompts should use the orchestrator route where possible.

## GPU-only policy

The orchestrator queues POST requests and checks free VRAM with `nvidia-smi` before forwarding. It also releases unrelated GPU users before a job starts:

- non-Ollama jobs stop loaded Ollama models
- non-Whisper jobs call Whisper `/api/deactivate`
- non-Comfy jobs call ComfyUI `/free`

For Ollama, strict mode checks `ollama ps` after requests and rejects results if a model is not reported as `100% GPU`. Auto-offload is enabled by default and unloads the service model after each queued job. The dashboard also exposes an `Alles entladen` button backed by `POST /api/offload`.

Whisper should be configured with CPU fallback disabled. In the companion local setup this means `WHISPER_CPU_FALLBACK=0`.

## Install

```bash
./install-user-service.sh
systemctl --user status gpu-orchestrator.service --no-pager
curl http://127.0.0.1:11435/api/status
```

## Environment

Important settings in `systemd/gpu-orchestrator.service`:

- `GPU_ORCH_PORT=11435`
- `GPU_ORCH_GPU_INDEX=0`
- `GPU_ORCH_STRICT_OLLAMA_GPU=1`
- `GPU_ORCH_AUTO_OFFLOAD=1`
- `GPU_ORCH_AUTO_OFFLOAD_DELAY_SECONDS=0`
- `GPU_ORCH_OLLAMA_MIN_FREE_MIB=2048`
- `GPU_ORCH_WHISPER_MIN_FREE_MIB=2500`
- `GPU_ORCH_COMFY_MIN_FREE_MIB=8192`

## Example Ollama request through the queue

```bash
curl -s -X POST http://127.0.0.1:11435/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3:8b","prompt":"Say GPU_OK","stream":false}'
```

## Notes

This is intentionally local-first infrastructure. It does not manage cloud GPUs and it does not attempt CPU fallback.
