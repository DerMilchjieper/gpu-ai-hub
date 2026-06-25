$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Tier = if ($args.Count -gt 0) { $args[0] } else { "minimal" }
$Profiles = Get-Content "config/models.json" -Raw | ConvertFrom-Json
$Models = $Profiles.$Tier
if (-not $Models) { throw "Unknown model tier: $Tier" }
foreach ($Model in $Models) {
  Write-Host "Pulling $($Model.model)"
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama pull $Model.model
  } else {
    docker compose --profile ollama exec ollama ollama pull $Model.model
  }
}
