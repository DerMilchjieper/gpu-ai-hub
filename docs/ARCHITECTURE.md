# GPU AI Hub architecture

Status: public alpha foundation.

## Product boundary

GPU AI Hub is a local-first control plane for AI tools. The web hub, service
registry, English message catalog, health checks, and setup workflow are portable. Model
runtimes remain replaceable providers because GPU support differs between
Linux, Windows/WSL2, and macOS.

## Hostnames

The zero-configuration browser URL is `http://ai-tool-hub.localhost:8191`.
Names below `.localhost` are reserved for loopback and do not require editing a
hosts file. Installers may optionally add `ai-tool-hub.local`, but `.local`
depends on mDNS or an administrator-managed hosts entry and is not the portable
default.

## Deployment layers

1. **Control plane**: English-language hub UI, service registry, health aggregation,
   recommended model catalog, and setup status.
2. **Portable tools**: chat/coder/vision clients, document RAG, n8n, and other
   services that can run in containers on all supported platforms.
3. **Accelerated providers**: Ollama, ComfyUI, Whisper, image/audio/video
   workers. These use Docker GPU profiles on supported NVIDIA hosts or native
   host endpoints on macOS and other unsupported Docker GPU environments.

## Configuration sources

- `config/services.json`: every navigation item, port, health endpoint, and
  installation profile.
- `config/models.json`: small/recommended/large model profiles and pull
  commands.
- `locales/en.json`: all user-facing control-plane strings.
- `.env`: host-specific endpoints and optional overrides; never committed with
  secrets.

No UI file should contain a workstation IP address or `/home/<user>` path.

## Security baseline

- Bind publicly reachable services to loopback by default.
- LAN access is an explicit opt-in.
- Do not render model output or filenames through unsanitized `innerHTML`.
- Validate uploaded filenames and enforce size limits.
- Destructive actions require an authenticated control-plane request.
- Status endpoints must not expose complete prompts or model responses.

## Platform support

| Capability | Linux NVIDIA | Windows + WSL2 | macOS Apple Silicon |
| --- | --- | --- | --- |
| Control plane | Docker | Docker Desktop | Docker Desktop |
| Ollama | native or Docker | native or WSL2 | native (Metal) |
| NVIDIA queue | supported | supported in WSL2 | unavailable |
| ComfyUI acceleration | NVIDIA container/native | WSL2/native | native Metal |
| Portable CPU fallback | opt-in | opt-in | opt-in |

The installer reports unsupported capabilities instead of silently moving a
GPU-only workflow to CPU.

## Scheduling and workers

Workers report accelerator capabilities and heartbeats to the control plane.
Jobs carry a mode, requirements, priority, service affinity, and an expiring
lease. Independent per-device provider instances are the default. Pooling is
only selected for compatible engines and oversized models. Apple Silicon is
treated as one Metal accelerator with unified memory.
