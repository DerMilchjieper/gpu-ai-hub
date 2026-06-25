#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

TIER=${1:-starter}
NATIVE_COMFY_DIR=${COMFYUI_NATIVE_DIR:-$HOME/.local/share/gpu-ai-hub/comfyui}
if [ -z "${COMFY_MODELS_DIR:-}" ] && [ -d "$NATIVE_COMFY_DIR" ]; then
  COMFY_MODELS_DIR="$NATIVE_COMFY_DIR/models"
else
  COMFY_MODELS_DIR=${COMFY_MODELS_DIR:-/opt/ComfyUI/models}
fi

case "$TIER" in
  starter|3d|video|all|list) ;;
  *) echo "Usage: $0 starter|3d|video|all|list"; exit 2;;
esac

if [ "$TIER" = list ]; then
  python3 - <<'PY'
import json
from pathlib import Path
data=json.loads(Path('config/comfyui.json').read_text())
for model in data['models']:
    mode='manual' if model.get('manual') else 'download'
    print(f"{model['tier']:7} {mode:8} {model['id']:16} -> {model['target']}")
PY
  exit 0
fi

echo "This script downloads only models with explicit Hugging Face repo/file metadata."
echo "Large or gated video models are printed as manual steps after license acceptance."
if [ "${GPU_AI_HUB_YES:-0}" != 1 ]; then
  printf "Continue for tier '%s'? [y/N] " "$TIER"
  read answer
  case "$answer" in y|Y) ;; *) exit 0;; esac
fi

if [ -d "$NATIVE_COMFY_DIR" ] && [ "$COMFY_MODELS_DIR" = "$NATIVE_COMFY_DIR/models" ]; then
  RUNNER="$NATIVE_COMFY_DIR/.venv/bin/python"
elif docker compose ps comfyui >/dev/null 2>&1; then
  RUNNER="docker compose --profile creative run --rm --no-deps -e TARGET_TIER=$TIER -e COMFY_MODELS_DIR=$COMFY_MODELS_DIR -v $ROOT/config:/workspace/config:ro -w /workspace comfyui python"
else
  RUNNER="python3"
fi

$RUNNER - <<'PY'
import json, os, shutil
from pathlib import Path
from huggingface_hub import hf_hub_download

tier=os.environ.get('TARGET_TIER','starter')
models_dir=Path(os.environ.get('COMFY_MODELS_DIR','/opt/ComfyUI/models'))
data=json.loads(Path('config/comfyui.json').read_text())
tiers={'starter':['starter'], '3d':['starter','3d'], 'video':['video'], 'all':['starter','3d','video']}[tier]
manual=[]
for model in data['models']:
    if model['tier'] not in tiers:
        continue
    target=models_dir/model['target']
    if model.get('manual'):
        manual.append(model)
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {model['id']} -> {target}")
    downloaded=Path(hf_hub_download(model['repo'], model['file']))
    if target.exists():
        print(f"Already exists: {target}")
    else:
        shutil.copy2(downloaded, target)

if manual:
    print('\nManual model files required after accepting upstream licenses:')
    for model in manual:
        print(f"- {model['id']}: place at {models_dir/model['target']}")
        print(f"  {model.get('note','')}")
PY

echo "ComfyUI model preparation completed for tier: $TIER"
