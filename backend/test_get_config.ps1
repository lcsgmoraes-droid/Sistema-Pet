# Sprint 2 - Finalização WhatsApp Config Test
$BASE_URL = "http://localhost:8000"

# Login e select tenant
$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body (@{email="admin@test.com"; password="admin123"} | ConvertTo-Json)

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token

$selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} `
    -Body (@{tenant_id=$tenant_id} | ConvertTo-Json)

$finalToken = $selectResponse.access_token

Write-Host "`n=== TESTE GET CONFIG ===" -ForegroundColor Cyan

try {
    $config = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config" `
        -Method GET `
        -Headers @{"Authorization"="Bearer $finalToken"}
    
    if ($config) {
        Write-Host "[OK] Config encontrada!" -ForegroundColor Green
        Write-Host "ID: $($config.id)" -ForegroundColor Gray
        Write-Host "Provider: $($config.provider)" -ForegroundColor Gray
        Write-Host "Model: $($config.model_preference)" -ForegroundColor Gray
    } else {
        Write-Host "[INFO] Nenhuma config" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

Write-Host ""
