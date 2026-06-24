#!/usr/bin/env sh
set -eu
TIER=${1:-minimal}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODELS=$(python3 -c 'import json,sys; print("\n".join(x["model"] for x in json.load(open(sys.argv[1]))[sys.argv[2]]))' "$ROOT/config/models.json" "$TIER")
for model in $MODELS; do
  echo "Pulling $model"
  if command -v ollama >/dev/null 2>&1; then ollama pull "$model"
  else (cd "$ROOT" && docker compose --profile ollama exec ollama ollama pull "$model")
  fi
done
