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
$env:LOGICFP_HANDLER_REGISTRARS = $HandlerRegistrars
$env:LOGICFP_BACKEND_TYPE = $BackendType
$env:LOGICFP_INSTANCE_ID = $InstanceId
$env:LOGICFP_DEFAULT_SOURCE = $DefaultSource

$command = @(
    "uv",
    "run",
    "uvicorn",
    "logicfp.app_factory:app",
    "--host",
    $BindHost,
    "--port",
    $Port
)

Write-Host "Workspace: $workspaceRoot"
Write-Host "PYTHONPATH=$env:PYTHONPATH"
Write-Host "LOGICFP_HANDLER_REGISTRARS=$env:LOGICFP_HANDLER_REGISTRARS"
Write-Host "LOGICFP_BACKEND_TYPE=$env:LOGICFP_BACKEND_TYPE"
Write-Host "LOGICFP_INSTANCE_ID=$env:LOGICFP_INSTANCE_ID"
Write-Host "LOGICFP_DEFAULT_SOURCE=$env:LOGICFP_DEFAULT_SOURCE"
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
