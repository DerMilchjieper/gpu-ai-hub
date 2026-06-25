#!/usr/bin/env sh
set -eu

TARGET="${1:-${COMFYUI_NATIVE_DIR:-$HOME/.local/share/gpu-ai-hub/comfyui}}"
CUSTOM_NODES="$TARGET/custom_nodes"
PYTHON="$TARGET/.venv/bin/python"

[ -d "$TARGET" ] || { echo "ComfyUI directory not found: $TARGET"; exit 1; }
[ -x "$PYTHON" ] || { echo "ComfyUI venv not found: $PYTHON"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Git is required."; exit 1; }

mkdir -p "$CUSTOM_NODES"

install_node() {
  repo="$1"
  dir="$2"
  ref="$3"
  if [ ! -d "$CUSTOM_NODES/$dir/.git" ]; then
    git clone "$repo" "$CUSTOM_NODES/$dir"
  fi
  git -C "$CUSTOM_NODES/$dir" fetch --depth 1 origin "$ref" >/dev/null 2>&1 || true
  git -C "$CUSTOM_NODES/$dir" checkout "$ref"
  git -C "$CUSTOM_NODES/$dir" submodule update --init --recursive
  if [ -f "$CUSTOM_NODES/$dir/requirements.txt" ]; then
    "$PYTHON" -m pip install -r "$CUSTOM_NODES/$dir/requirements.txt"
  fi
}

install_node https://github.com/ltdrdata/ComfyUI-Manager.git ComfyUI-Manager main
install_node https://github.com/kijai/ComfyUI-KJNodes.git ComfyUI-KJNodes 588badc5252c2b483c8b37110f155973cf39e325
install_node https://github.com/kijai/ComfyUI-WanVideoWrapper.git ComfyUI-WanVideoWrapper 088128b224242e110d3906c6750e9a3a348a659b
install_node https://github.com/flowtyone/ComfyUI-Flowty-TripoSR.git ComfyUI-Flowty-TripoSR a0c94ac60a7cc062604f61aeeea6d0d493521de3
install_node https://github.com/yolain/ComfyUI-Easy-Use.git ComfyUI-Easy-Use 54d080bf6a4f52da287e984f305243c10db097f5
install_node https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git ComfyUI-VideoHelperSuite 4ee72c065db22c9d96c2427954dc69e7b908444b
install_node https://github.com/Stability-AI/stable-fast-3d.git stable-fast-3d ff21fc491b4dc5314bf6734c7c0dabd86b5f5bb2

"$PYTHON" -m pip install huggingface-hub==0.36.2 onnxruntime-gpu==1.20.1

echo "ComfyUI custom nodes installed in $CUSTOM_NODES"
