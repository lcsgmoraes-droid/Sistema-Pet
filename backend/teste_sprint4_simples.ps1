# Teste Sprint 4 - Simples
$ErrorActionPreference = "Stop"
$BASE_URL = "http://localhost:8000"

Write-Host "`n=== TESTE SPRINT 4 ===" -ForegroundColor Cyan

# 1. Health check
try {
    $health = Invoke-RestMethod -Uri "$BASE_URL/health" -Method GET -TimeoutSec 5
    Write-Host "[OK] Backend online" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Backend offline" -ForegroundColor Red
    exit 1
}

# 2. Login
$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body '{"email":"admin@test.com","password":"test123"}'

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token

# 3. Select tenant
$selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} `
    -Body "{`"tenant_id`":`"$tenant_id`"}"

$finalToken = $selectResponse.access_token

# 4. Criar agent
Write-Host "`n[1] Criando agent..." -ForegroundColor Yellow
try {
    $agent = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/agents" `
        -Method POST `
        -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} `
        -Body '{"name":"Joao Silva","email":"joao@petshop.com","status":"available","max_concurrent_chats":5}'
    Write-Host "    OK - ID: $($agent.id)" -ForegroundColor Green
} catch {
    $err = $_.ErrorDetails.Message | ConvertFrom-Json
    if ($err.detail -like "*already exists*") {
        Write-Host "    OK (ja existe)" -ForegroundColor Cyan
    } else {
        Write-Host "    ERRO: $($err.detail)" -ForegroundColor Red
    }
}

# 5. Listar agents
Write-Host "`n[2] Listando agents..." -ForegroundColor Yellow
$agents = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/agents" `
    -Method GET `
    -Headers @{"Authorization"="Bearer $finalToken"}
Write-Host "    OK - Total: $($agents.Count)" -ForegroundColor Green

# 6. Testar sentiment
Write-Host "`n[3] Testando sentiment..." -ForegroundColor Yellow
$sentiment = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-sentiment" `
    -Method POST `
    -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} `
    -Body '{"message":"Estou muito irritado!"}'
Write-Host "    OK - Score: $($sentiment.score) | Should handoff: $($sentiment.should_handoff)" -ForegroundColor Green

# 7. Stats
Write-Host "`n[4] Buscando stats..." -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/handoffs/dashboard/stats" `
    -Method GET `
    -Headers @{"Authorization"="Bearer $finalToken"}
Write-Host "    OK - Pending: $($stats.pending_count) | Active: $($stats.active_count)" -ForegroundColor Green

Write-Host "`n=== SPRINT 4 COMPLETA! ===" -ForegroundColor Green
Write-Host "Todos os endpoints funcionando!" -ForegroundColor Gray
