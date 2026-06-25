#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
command -v docker >/dev/null 2>&1 || { echo "Docker is required: https://docs.docker.com/get-docker/"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required."; exit 1; }
[ -f .env ] || cp .env.example .env
IP=""
case "$(uname -s)" in
  Darwin) IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true) ;;
  Linux) IP=$(hostname -I 2>/dev/null | awk '{print $1}') ;;
esac
export HUB_MDNS_ADDRESS="$IP"
PROFILE_ARGS=""
COMPOSE_FILES="-f compose.yaml"
GPU="cpu"
FULL_TOOLPACK=0
APPLE_NATIVE_COMFY=0
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU="nvidia"; COMPOSE_FILES="$COMPOSE_FILES -f compose.nvidia.yaml"
elif [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ]; then
  GPU="apple"
elif command -v rocm-smi >/dev/null 2>&1; then
  GPU="amd"
fi
echo "Detected accelerator backend: $GPU"
if command -v ollama >/dev/null 2>&1; then
  echo "Found native Ollama; the hub will probe it through host.docker.internal:11434."
  sed -i.bak 's#^OLLAMA_BASE_URL=.*#OLLAMA_BASE_URL=http://host.docker.internal:11434#' .env
else
  printf "No native Ollama found. Start bundled Ollama? [Y/n] "
  read answer || true
  case "${answer:-Y}" in n|N) ;; *) PROFILE_ARGS="$PROFILE_ARGS --profile ollama";; esac
fi
printf "Install full tool pack (ComfyUI workflows, Whisper, SearXNG, n8n)? [Y/n] "
read extras || true
case "${extras:-Y}" in
  n|N) ;;
  *) PROFILE_ARGS="$PROFILE_ARGS --profile research --profile automation --profile speech"
     FULL_TOOLPACK=1
     if [ "$GPU" = apple ]; then APPLE_NATIVE_COMFY=1; "$ROOT/scripts/install-comfyui-native.sh"
     else PROFILE_ARGS="$PROFILE_ARGS --profile creative"; fi ;;
esac
printf "Expose ComfyUI and Whisper directly to your trusted LAN? [y/N] "
read lan_expose || true
case "${lan_expose:-N}" in
  y|Y)
    sed -i.bak 's/^COMFYUI_BIND=.*/COMFYUI_BIND=0.0.0.0/;s/^WHISPER_BIND=.*/WHISPER_BIND=0.0.0.0/' .env
    ;;
esac
docker compose $COMPOSE_FILES $PROFILE_ARGS up -d --build
printf "Download starter Ollama chat models now? [Y/n] "
read ollama_models || true
case "${ollama_models:-Y}" in n|N) ;; *) "$ROOT/scripts/pull-models.sh" minimal;; esac
if [ "$FULL_TOOLPACK" = 1 ]; then
  printf "Download ComfyUI starter model now (SDXL, about 7 GB)? [Y/n] "
  read comfy_starter || true
  case "${comfy_starter:-Y}" in n|N) ;; *) GPU_AI_HUB_YES=1 "$ROOT/scripts/pull-comfy-models.sh" starter;; esac
  printf "Download ComfyUI 3D helper models now? [Y/n] "
  read comfy_3d || true
  case "${comfy_3d:-Y}" in n|N) ;; *) GPU_AI_HUB_YES=1 "$ROOT/scripts/pull-comfy-models.sh" 3d;; esac
fi
echo "GPU AI Hub started."
echo "Preferred URL: http://ai-tool-hub.local/"
[ -n "$IP" ] && echo "LAN fallback: http://$IP/"
if command -v avahi-publish-address >/dev/null 2>&1 && [ -n "$IP" ]; then
  echo "Linux mDNS available. Run persistently: avahi-publish-address -R ai-tool-hub.local $IP"
fi
echo "Read the generated admin password with: docker compose logs hub"
echo "Model recommendations are shown in the Setup tab after login."
echo "Manual model pull example: scripts/pull-models.sh recommended"
echo "Starter image model: scripts/pull-comfy-models.sh starter"
echo "3D helper models: scripts/pull-comfy-models.sh 3d"
echo "Video model target paths: scripts/pull-comfy-models.sh video"
echo "Curated ComfyUI workflows: workflows/comfyui/"
