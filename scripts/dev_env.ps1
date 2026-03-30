$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$UvCacheDir = Join-Path $ProjectRoot ".uv-cache"
$TempDir = Join-Path $ProjectRoot ".tmp"
$PytestRoot = Join-Path $ProjectRoot ".pytest_tmp"

New-Item -ItemType Directory -Force $UvCacheDir | Out-Null
New-Item -ItemType Directory -Force $TempDir | Out-Null
New-Item -ItemType Directory -Force $PytestRoot | Out-Null

$env:UV_CACHE_DIR = $UvCacheDir
$env:TMP = $TempDir
$env:TEMP = $TempDir

Write-Host "Project cache/temp environment enabled:"
Write-Host "  UV_CACHE_DIR = $env:UV_CACHE_DIR"
Write-Host "  TMP          = $env:TMP"
Write-Host "  TEMP         = $env:TEMP"
Write-Host "  pytest       = .pytest_tmp/basetemp (configured in pyproject.toml)"
