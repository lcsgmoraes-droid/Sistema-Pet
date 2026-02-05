# Teste detalhado Sprint 4
$ErrorActionPreference = "Continue"
$BASE_URL = "http://localhost:8000"

Write-Host "`n=== TESTE DETALHADO SPRINT 4 ===" -ForegroundColor Cyan

# 1. Login
Write-Host "`n[1] Login..." -ForegroundColor Yellow
$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body '{"email":"admin@test.com","password":"test123"}'

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token
Write-Host "    OK - Tenant: $tenant_id" -ForegroundColor Green

# 2. Select tenant
$selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} `
    -Body "{`"tenant_id`":`"$tenant_id`"}"

$finalToken = $selectResponse.access_token
Write-Host "    OK - Token final obtido" -ForegroundColor Green

# 3. Criar agent com mais detalhes
Write-Host "`n[2] Criando agent..." -ForegroundColor Yellow
try {
    $agentBody = @{
        name = "Joao Silva"
        email = "joao@petshop.com"
        status = "online"
        max_concurrent_chats = 5
    } | ConvertTo-Json
    
    Write-Host "    Body: $agentBody" -ForegroundColor Gray
    
    $agent = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/agents" `
        -Method POST `
        -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} `
        -Body $agentBody
    
    Write-Host "    OK - Agent criado!" -ForegroundColor Green
    Write-Host "    ID: $($agent.id)" -ForegroundColor Gray
    Write-Host "    Nome: $($agent.name)" -ForegroundColor Gray
} catch {
    Write-Host "    ERRO!" -ForegroundColor Red
    Write-Host "    Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    Write-Host "    Mensagem: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

# 4. Testar sentiment com detalhes
Write-Host "`n[3] Testando sentiment..." -ForegroundColor Yellow
try {
    $sentimentBody = @{
        message = "Estou muito irritado!"
    } | ConvertTo-Json
    
    Write-Host "    Body: $sentimentBody" -ForegroundColor Gray
    
    $sentiment = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-sentiment" `
        -Method POST `
        -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} `
        -Body $sentimentBody
    
    Write-Host "    OK - Sentiment analisado!" -ForegroundColor Green
    Write-Host "    Score: $($sentiment.score)" -ForegroundColor Gray
    Write-Host "    Emotion: $($sentiment.emotion)" -ForegroundColor Gray
    Write-Host "    Should handoff: $($sentiment.should_handoff)" -ForegroundColor Gray
} catch {
    Write-Host "    ERRO!" -ForegroundColor Red
    Write-Host "    Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    Write-Host "    Mensagem: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host "`n=== FIM ===" -ForegroundColor Cyan
