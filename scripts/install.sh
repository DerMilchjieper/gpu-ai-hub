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
if command -v ollama >/dev/null 2>&1; then
  echo "Found native Ollama; the hub will probe it through host.docker.internal:11434."
else
  printf "No native Ollama found. Start bundled Ollama? [Y/n] "
  read answer || true
  case "${answer:-Y}" in n|N) ;; *) PROFILE_ARGS="$PROFILE_ARGS --profile ollama";; esac
fi
printf "Start bundled SearXNG research and n8n automation? [Y/n] "
read extras || true
case "${extras:-Y}" in n|N) ;; *) PROFILE_ARGS="$PROFILE_ARGS --profile research --profile automation";; esac
docker compose $PROFILE_ARGS up -d --build
echo "GPU AI Hub started."
echo "Preferred URL: http://ai-tool-hub.local/"
[ -n "$IP" ] && echo "LAN fallback: http://$IP/"
if command -v avahi-publish-address >/dev/null 2>&1 && [ -n "$IP" ]; then
  echo "Linux mDNS available. Run persistently: avahi-publish-address -R ai-tool-hub.local $IP"
fi
echo "Read the generated admin password with: docker compose logs hub"
echo "Recommended models: scripts/pull-models.sh minimal"
