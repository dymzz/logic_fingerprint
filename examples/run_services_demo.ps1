param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [string]$BackendType = "memory",
    [string]$InstanceId = "prod-node-a",
    [string]$DefaultSource = "api",
    [int]$BaseStock = 24,
    [double]$DiscountRate = 0.10,
    [double]$TaxRate = 0.06,
    [string]$Currency = "CNY",
    [switch]$ShowCommand
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = ".;src"
$env:LOGIC_FINGERPRINT_HANDLER_REGISTRARS = "examples.production_services"
$env:LOGIC_FINGERPRINT_BACKEND_TYPE = $BackendType
$env:LOGIC_FINGERPRINT_INSTANCE_ID = $InstanceId
$env:LOGIC_FINGERPRINT_DEFAULT_SOURCE = $DefaultSource
$env:EXAMPLE_BASE_STOCK = "$BaseStock"
$env:EXAMPLE_DISCOUNT_RATE = "$DiscountRate"
$env:EXAMPLE_TAX_RATE = "$TaxRate"
$env:EXAMPLE_CURRENCY = $Currency

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
Write-Host "EXAMPLE_BASE_STOCK=$env:EXAMPLE_BASE_STOCK"
Write-Host "EXAMPLE_DISCOUNT_RATE=$env:EXAMPLE_DISCOUNT_RATE"
Write-Host "EXAMPLE_TAX_RATE=$env:EXAMPLE_TAX_RATE"
Write-Host "EXAMPLE_CURRENCY=$env:EXAMPLE_CURRENCY"
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
