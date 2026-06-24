#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
TIER=${1:-starter}
case "$TIER" in
  starter)
    echo "This downloads the SDXL 1.0 base checkpoint (about 7 GB)."
    echo "By continuing you accept the model license published by Stability AI."
    printf "Continue? [y/N] "; read answer
    case "$answer" in y|Y) ;; *) exit 0;; esac
    docker compose --profile creative run --rm --no-deps comfyui python -c 'from huggingface_hub import hf_hub_download; hf_hub_download("stabilityai/stable-diffusion-xl-base-1.0","sd_xl_base_1.0.safetensors",local_dir="/opt/ComfyUI/models/checkpoints")'
    ;;
  large)
    echo "Wan 2.2 and 3D model packs are workflow-specific and may be gated."
    echo "Open ComfyUI Manager and install the models reported as missing by each workflow."
    ;;
  *) echo "Usage: $0 starter|large"; exit 2;;
esac
