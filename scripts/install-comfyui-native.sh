#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TARGET="${COMFYUI_NATIVE_DIR:-$HOME/.local/share/gpu-ai-hub/comfyui}"
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required for native ComfyUI."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Git is required for native ComfyUI."; exit 1; }
mkdir -p "$(dirname "$TARGET")"
[ -d "$TARGET/.git" ] || git clone https://github.com/comfyanonymous/ComfyUI.git "$TARGET"
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/pip" install --upgrade pip comfy-cli
(cd "$TARGET" && "$TARGET/.venv/bin/pip" install -r requirements.txt)
"$ROOT/scripts/install-comfyui-nodes.sh" "$TARGET"
mkdir -p "$TARGET/user/default/workflows"
cp "$ROOT"/workflows/comfyui/*.json "$TARGET/user/default/workflows/"
echo "Native ComfyUI installed in $TARGET"
echo "Launch: $TARGET/.venv/bin/python $TARGET/main.py --listen 0.0.0.0 --port 8188 --enable-manager"
