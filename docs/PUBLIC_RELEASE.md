# Public release checklist

Before changing repository visibility:

- verify the included Apache-2.0 license and copyright owner;
- enable private vulnerability reporting and Dependabot alerts;
- protect `main`, require CI, and disable force pushes;
- add repository topics: local-ai, self-hosted, ollama, comfyui, whisper, gpu;
- confirm the current tree contains no secrets or machine-specific data.

Before a stable tag, run clean-host installations on Linux NVIDIA, Windows 11
with Docker Desktop, and Apple Silicon, then build every image without cache
and review all workflow/model licenses.

ComfyUI release requirements:

- `config/comfyui.json` must list every workflow, required custom node bundle,
  and required model file path;
- Docker ComfyUI builds must include the custom node bundles needed by the
  bundled workflows;
- native ComfyUI installs must run `scripts/install-comfyui-nodes.sh`;
- `scripts/pull-comfy-models.sh starter` and `3d` should pull every
  non-gated file with explicit Hugging Face metadata;
- large/gated video models may stay manual, but the script must print exact
  target paths.
