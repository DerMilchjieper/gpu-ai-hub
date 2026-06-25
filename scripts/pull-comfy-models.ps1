$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Tier = if ($args.Count -gt 0) { $args[0] } else { "starter" }
if ($Tier -notin @("starter", "3d", "video", "all", "list")) { throw "Usage: .\scripts\pull-comfy-models.ps1 starter|3d|video|all|list" }
$Config = Get-Content "config/comfyui.json" -Raw | ConvertFrom-Json
if ($Tier -eq "list") {
  foreach ($Model in $Config.models) {
    $Mode = if ($Model.manual) { "manual" } else { "download" }
    Write-Host ("{0,-7} {1,-8} {2,-16} -> {3}" -f $Model.tier, $Mode, $Model.id, $Model.target)
  }
  exit 0
}
Write-Host "This script downloads only models with explicit Hugging Face repo/file metadata."
Write-Host "Large or gated video models are printed as manual steps after license acceptance."
if ($env:GPU_AI_HUB_YES -ne "1") {
  $Answer = Read-Host "Continue for tier '$Tier'? [y/N]"
  if ($Answer -notmatch "^[yY]$") { exit 0 }
}
$ConfigDir = Join-Path $Root "config"
docker compose --profile creative run --rm --no-deps `
  -e TARGET_TIER=$Tier `
  -e COMFY_MODELS_DIR=/opt/ComfyUI/models `
  -v "${ConfigDir}:/workspace/config:ro" `
  -w /workspace `
  comfyui python -c @'
import json, os, shutil
from pathlib import Path
from huggingface_hub import hf_hub_download
tier=os.environ.get('TARGET_TIER','starter')
models_dir=Path(os.environ.get('COMFY_MODELS_DIR','/opt/ComfyUI/models'))
data=json.loads(Path('config/comfyui.json').read_text())
tiers={'starter':['starter'], '3d':['starter','3d'], 'video':['video'], 'all':['starter','3d','video']}[tier]
manual=[]
for model in data['models']:
    if model['tier'] not in tiers:
        continue
    target=models_dir/model['target']
    if model.get('manual'):
        manual.append(model)
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {model['id']} -> {target}")
    downloaded=Path(hf_hub_download(model['repo'], model['file']))
    if target.exists():
        print(f"Already exists: {target}")
    else:
        shutil.copy2(downloaded, target)
if manual:
    print('\nManual model files required after accepting upstream licenses:')
    for model in manual:
        print(f"- {model['id']}: place at {models_dir/model['target']}")
        print(f"  {model.get('note','')}")
'@
Write-Host "ComfyUI model preparation completed for tier: $Tier"
