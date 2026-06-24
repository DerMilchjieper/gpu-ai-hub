$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is required: https://docs.docker.com/desktop/install/windows-install/" }
docker compose version | Out-Null
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
$Ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } | Select-Object -First 1 -ExpandProperty IPAddress)
$env:HUB_MDNS_ADDRESS = $Ip
$Profiles = @()
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  Write-Host "Found native Ollama; using host.docker.internal:11434."
} else {
  $Answer = Read-Host "No native Ollama found. Start bundled Ollama? [Y/n]"
  if ($Answer -notmatch "^[nN]$") { $Profiles += @("--profile","ollama") }
}
$Extras = Read-Host "Start bundled SearXNG and n8n? [Y/n]"
if ($Extras -notmatch "^[nN]$") { $Profiles += @("--profile","research","--profile","automation") }
& docker compose @Profiles up -d --build
Write-Host "Preferred URL: http://ai-tool-hub.local/"
Write-Host "LAN fallback: http://$Ip/"
Write-Host "Initial password: docker compose logs hub"
