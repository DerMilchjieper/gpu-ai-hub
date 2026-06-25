$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Failed = $false
function Check($Label, [scriptblock]$Command) {
  try {
    & $Command | Out-Null
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    Write-Host "ok   $Label"
  } catch {
    Write-Host "fail $Label"
    $script:Failed = $true
  }
}
function Warn($Label, [scriptblock]$Command) {
  try {
    & $Command | Out-Null
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    Write-Host "ok   $Label"
  } catch {
    Write-Host "warn $Label"
  }
}
Check "Docker CLI" { docker --version }
Check "Docker Compose v2" { docker compose version }
Warn "NVIDIA GPU visible" { nvidia-smi }
Warn "Ollama CLI visible" { ollama --version }
Check "compose.yaml present" { if (-not (Test-Path "compose.yaml")) { throw "missing" } }
Warn ".env present after first install" { if (-not (Test-Path ".env")) { throw "missing" } }
Check "ComfyUI config JSON" { Get-Content "config/comfyui.json" -Raw | ConvertFrom-Json }
Check "service config JSON" { Get-Content "config/services.json" -Raw | ConvertFrom-Json }
Check "bundled ComfyUI workflow files" {
  $Config = Get-Content "config/comfyui.json" -Raw | ConvertFrom-Json
  foreach ($Workflow in $Config.workflows) {
    if (-not (Test-Path (Join-Path "workflows/comfyui" $Workflow.file))) { throw "missing $($Workflow.file)" }
  }
}
try { docker compose ps } catch { Write-Host "warn Docker Compose project is not running yet" }
Write-Host ""
Write-Host "Next useful commands:"
Write-Host "  .\scripts\install.ps1"
Write-Host "  .\scripts\pull-models.ps1 minimal"
Write-Host "  .\scripts\pull-comfy-models.ps1 starter"
Write-Host "  .\scripts\pull-comfy-models.ps1 3d"
Write-Host "  .\scripts\pull-comfy-models.ps1 video"
if ($Failed) { exit 1 }
