param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Invoke-Handler {
    param(
        [string]$Handler,
        [hashtable]$Payload
    )

    $body = @{
        handler = $Handler
        payload = $Payload
    } | ConvertTo-Json -Depth 6

    Write-Host ""
    Write-Host "POST $BaseUrl/execute_handler [$Handler]"
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUrl/execute_handler" `
        -ContentType "application/json" `
        -Body $body

    $response | ConvertTo-Json -Depth 8
}

Invoke-Handler -Handler "inventory_lookup" -Payload @{
    sku = "SKU-1001"
    warehouse = "main"
}

Invoke-Handler -Handler "order_quote" -Payload @{
    order_id = "ORDER-42"
    items = @(12, 18, 30)
}
