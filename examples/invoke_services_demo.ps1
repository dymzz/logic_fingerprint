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

Invoke-Handler -Handler "inventory_snapshot" -Payload @{
    sku = "SKU-9000"
    warehouse = "east"
}

Invoke-Handler -Handler "order_quote_with_services" -Payload @{
    order_id = "ORDER-7"
    items = @(10, 20, 30)
}
