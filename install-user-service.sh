#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${HOME}/.config/systemd/user"
mkdir -p "${HOME}/gpu-orchestrator"
cp "${ROOT}/src/gpu_orchestrator.py" "${HOME}/gpu-orchestrator/gpu_orchestrator.py"
chmod +x "${HOME}/gpu-orchestrator/gpu_orchestrator.py"
cp "${ROOT}/systemd/gpu-orchestrator.service" "${HOME}/.config/systemd/user/gpu-orchestrator.service"
systemctl --user daemon-reload
systemctl --user enable --now gpu-orchestrator.service
