#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
FAIL=0

check() {
  label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "ok   $label"
  else
    echo "fail $label"
    FAIL=1
  fi
}

warn() {
  label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "ok   $label"
  else
    echo "warn $label"
  fi
}

check "Docker CLI" command -v docker
check "Docker Compose v2" docker compose version
warn "NVIDIA GPU visible" command -v nvidia-smi
warn "Ollama CLI visible" command -v ollama
check "compose.yaml present" test -f compose.yaml
warn ".env present after first install" test -f .env
check "ComfyUI config JSON" python3 -m json.tool config/comfyui.json
check "service config JSON" python3 -m json.tool config/services.json
check "ComfyUI pull script executable" test -x scripts/pull-comfy-models.sh
check "ComfyUI node script executable" test -x scripts/install-comfyui-nodes.sh

python3 - <<'PY'
import json, sys
from pathlib import Path
root=Path('.')
config=json.loads(Path('config/comfyui.json').read_text())
missing=[]
for workflow in config['workflows']:
    path=root/'workflows/comfyui'/workflow['file']
    if not path.exists(): missing.append(str(path))
if missing:
    print('fail missing workflow files:')
    for item in missing: print('     '+item)
    sys.exit(1)
print('ok   bundled ComfyUI workflow files')
PY

if docker compose ps >/dev/null 2>&1; then
  echo "ok   Docker Compose project readable"
  docker compose ps
else
  echo "warn Docker Compose project is not running yet"
fi

echo
echo "Next useful commands:"
echo "  ./scripts/install.sh"
echo "  ./scripts/pull-models.sh minimal"
echo "  ./scripts/pull-comfy-models.sh starter"
echo "  ./scripts/pull-comfy-models.sh 3d"
echo "  ./scripts/pull-comfy-models.sh video"

exit "$FAIL"
