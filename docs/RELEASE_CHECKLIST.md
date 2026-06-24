# Public alpha release checklist

## Required before publishing a tagged release

- [x] Remove workstation IP addresses and absolute home paths from portable code.
- [x] Add authenticated LAN control plane and CSRF protection.
- [x] Add English/German locale parity test.
- [x] Add Dockerfile, Compose stack, Caddy gateway, and OS bootstrap scripts.
- [x] Add private-network discovery limits and explicit service acceptance.
- [x] Add hardware inventory and topology recommendations.
- [x] Add persistent local and remote-worker Ollama job execution.
- [x] Build and smoke-test the control-plane image.
- [ ] Choose and add the project license.
- [ ] Test Compose on a clean Linux host with Compose v2.
- [ ] Test the PowerShell installer on Windows 11 + Docker Desktop.
- [ ] Test the shell installer on Apple Silicon + Docker Desktop + native Ollama.
- [x] Add reproducible ComfyUI and Whisper provider builds with curated workflows.
- [ ] Pin every ComfyUI custom-node repository to an audited commit.
- [ ] Verify all large/gated model download instructions and licenses.
- [ ] Add HTTPS/private-access guidance for untrusted LANs.

## Release boundary

The portable control plane and Ollama worker path are alpha-supported. Files
under `src/`, `systemd/`, and `landing-page/` are legacy workstation assets
until migrated behind the portable registry and security boundary.
