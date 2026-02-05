# Test WhatsApp Config with detailed error
$BASE_URL = "http://localhost:8000"
$OPENAI_KEY = "sk-proj-U5ClBgQjRpnJ3xCAmXlyshqjXbU-hePvydc61GHZ0QZo9mlVf7Kbi5JVpTcNSV6--J5jJsdWxqT3BlbkFJ76jgPB8VuHZ6kJRTSpF1j_8-gxojKj761rFXAts8ZSQIPhmKBjzbhDghDZ54TjEhl0rhR4ikA"

Write-Host "1. Login..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@test.com"
    password = "admin123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $loginBody

$token = $loginResponse.access_token
Write-Host "Token: OK" -ForegroundColor Green

Write-Host "`n2. Select Tenant..." -ForegroundColor Yellow
$tenant_id = $loginResponse.tenants[0].id
$selectBody = @{ tenant_id = $tenant_id } | ConvertTo-Json
$selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Headers @{
        "Content-Type"="application/json"
        "Authorization"="Bearer $token"
    } `
    -Body $selectBody

$finalToken = $selectResponse.access_token
Write-Host "Tenant ID: $tenant_id" -ForegroundColor Green

Write-Host "`n3. POST Config..." -ForegroundColor Yellow
$configBody = @{
    provider = "360dialog"
    openai_api_key = $OPENAI_KEY
    model_preference = "gpt-4o-mini"
    auto_response_enabled = $true
    bot_name = "Assistente Pet Shop"
    greeting_message = "Ola! Sou o assistente virtual. Como posso ajudar?"
    tone = "friendly"
} | ConvertTo-Json

Write-Host "Body:" -ForegroundColor Gray
Write-Host $configBody -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/api/whatsapp/config" `
        -Method POST `
        -Headers @{
            "Content-Type"="application/json"
            "Authorization"="Bearer $finalToken"
        } `
        -Body $configBody
    
    Write-Host "`nSUCESSO!" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | ConvertTo-Json
} catch {
    Write-Host "`nERRO:" -ForegroundColor Red
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    
    $result = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($result)
    $reader.BaseStream.Position = 0
    $responseBody = $reader.ReadToEnd()
    
    Write-Host "Response Body:" -ForegroundColor Red
    Write-Host $responseBody -ForegroundColor Red
}
