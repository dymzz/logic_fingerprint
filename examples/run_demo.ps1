param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [string]$HandlerRegistrars = "examples.production_handlers",
    [string]$BackendType = "memory",
    [string]$InstanceId = "prod-node-a",
    [string]$DefaultSource = "api",
    [switch]$ShowCommand
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = ".;src"
$env:LOGIC_FINGERPRINT_HANDLER_REGISTRARS = $HandlerRegistrars
$env:LOGIC_FINGERPRINT_BACKEND_TYPE = $BackendType
$env:LOGIC_FINGERPRINT_INSTANCE_ID = $InstanceId
$env:LOGIC_FINGERPRINT_DEFAULT_SOURCE = $DefaultSource

$command = @(
    "uv",
    "run",
    "uvicorn",
    "logic_fingerprint.app_factory:app",
    "--host",
    $BindHost,
    "--port",
    $Port
)

Write-Host "Workspace: $workspaceRoot"
Write-Host "PYTHONPATH=$env:PYTHONPATH"
Write-Host "LOGIC_FINGERPRINT_HANDLER_REGISTRARS=$env:LOGIC_FINGERPRINT_HANDLER_REGISTRARS"
Write-Host "LOGIC_FINGERPRINT_BACKEND_TYPE=$env:LOGIC_FINGERPRINT_BACKEND_TYPE"
Write-Host "LOGIC_FINGERPRINT_INSTANCE_ID=$env:LOGIC_FINGERPRINT_INSTANCE_ID"
Write-Host "LOGIC_FINGERPRINT_DEFAULT_SOURCE=$env:LOGIC_FINGERPRINT_DEFAULT_SOURCE"
Write-Host "Command: $($command -join ' ')"

if ($ShowCommand) {
    exit 0
}

Push-Location $workspaceRoot
try {
    & $command[0] $command[1] $command[2] $command[3] $command[4] $command[5] $command[6] $command[7]
}
finally {
    Pop-Location
}
