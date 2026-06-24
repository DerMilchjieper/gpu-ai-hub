# Public release checklist

Before changing repository visibility:

- choose and add an OSI-approved project license;
- enable private vulnerability reporting and Dependabot alerts;
- protect `main`, require CI, and disable force pushes;
- add repository topics: local-ai, self-hosted, ollama, comfyui, whisper, gpu;
- confirm the current tree contains no secrets or machine-specific data.

Before a stable tag, run clean-host installations on Linux NVIDIA, Windows 11
with Docker Desktop, and Apple Silicon, then build every image without cache
and review all workflow/model licenses.
