$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required: https://docs.docker.com/desktop/install/windows-install/" }
docker compose version | Out-Null
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
$Ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } | Select-Object -First 1 -ExpandProperty IPAddress)
$env:HUB_MDNS_ADDRESS = $Ip
$Profiles = @()
$ComposeFiles = @("-f","compose.yaml")
$Gpu = "cpu"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  $Gpu = "nvidia"
  $ComposeFiles += @("-f","compose.nvidia.yaml")
}
Write-Host "Detected accelerator backend: $Gpu"
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  Write-Host "Found native Ollama; using host.docker.internal:11434."
  (Get-Content ".env") -replace "^OLLAMA_BASE_URL=.*", "OLLAMA_BASE_URL=http://host.docker.internal:11434" | Set-Content ".env"
} else {
  $Answer = Read-Host "No native Ollama found. Start bundled Ollama? [Y/n]"
  if ($Answer -notmatch "^[nN]$") { $Profiles += @("--profile","ollama") }
}
$Extras = Read-Host "Install full tool pack: ComfyUI workflows, Whisper, SearXNG and n8n? [Y/n]"
if ($Extras -notmatch "^[nN]$") { $Profiles += @("--profile","research","--profile","automation","--profile","creative","--profile","speech") }
& docker compose @ComposeFiles @Profiles up -d --build
Write-Host "Preferred URL: http://ai-tool-hub.local/"
Write-Host "LAN fallback: http://$Ip/"
Write-Host "Initial password: docker compose logs hub"
Write-Host "ComfyUI port: 8188"
Write-Host "Whisper API port: 8001"
Write-Host "Starter image model: scripts/pull-comfy-models.sh starter"
