# Script Simplificado - Configurar OpenAI

Write-Host "`n=== Configuracao OpenAI ===" -ForegroundColor Cyan

# Usar chave do sistema
$OPENAI_KEY = "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"

Write-Host "Usando chave configurada..." -ForegroundColor Green

Write-Host "`nFazendo login..." -ForegroundColor Cyan

# Login
$loginBody = @{
    email = "admin@test.com"
    password = "test123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login-multitenant" -Method POST -Headers @{"Content-Type"="application/json"} -Body $loginBody

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token

Write-Host "Login OK - Tenant: $tenant_id" -ForegroundColor Green

# Selecionar tenant
$selectBody = @{tenant_id=$tenant_id} | ConvertTo-Json
$selectResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/select-tenant" -Method POST -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} -Body $selectBody
$finalToken = $selectResponse.access_token

Write-Host "Tenant selecionado!" -ForegroundColor Green

# Salvar configuracao
Write-Host "`nSalvando configuracao..." -ForegroundColor Cyan

$configBody = @{
    openai_api_key = $OPENAI_KEY
    bot_name = "Assistente Pet Shop"
    tone = "friendly"
    model_preference = "gpt-4o-mini"
    max_tokens = 500
    temperature = 0.7
    auto_response_enabled = $true
    working_hours_start = "00:00:00"
    working_hours_end = "23:59:59"
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $configBody
    Write-Host "Config criada!" -ForegroundColor Green
} catch {
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" -Method PUT -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $configBody
        Write-Host "Config atualizada!" -ForegroundColor Green
    } catch {
        Write-Host "Erro: $_" -ForegroundColor Red
        exit 1
    }
}

# Testar
Write-Host "`nTestando com IA (aguarde 2-5s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

$testBody = @{
    message = "Oi! Quero comprar racao para cachorro"
    phone_number = "+5511999887766"
} | ConvertTo-Json

try {
    $test = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $testBody -TimeoutSec 30
    
    Write-Host "`n=== SUCESSO! ===" -ForegroundColor Green
    Write-Host "Intent: $($test.intent) ($($test.confidence))" -ForegroundColor Gray
    Write-Host "Tokens: $($test.tokens_used)" -ForegroundColor Gray
    Write-Host "Tempo: $([math]::Round($test.processing_time, 2))s" -ForegroundColor Gray
    Write-Host "`nResposta:" -ForegroundColor Cyan
    Write-Host $test.response -ForegroundColor White
    Write-Host "`nSprint 3 - 100% Funcional!" -ForegroundColor Green
} catch {
    Write-Host "`nErro no teste: $_" -ForegroundColor Red
}
