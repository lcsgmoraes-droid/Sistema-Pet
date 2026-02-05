# Teste Completo Sprint 4 - Human Handoff
$ErrorActionPreference = "Stop"
$BASE_URL = "http://localhost:8000"

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "  TESTE SPRINT 4 - HUMAN HANDOFF" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# 1. Login
Write-Host "`n[1/6] Fazendo login..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@test.com"
    password = "admin123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $loginBody

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token
Write-Host "   ✓ Login OK - Tenant: $tenant_id" -ForegroundColor Green

# 2. Select Tenant
Write-Host "`n[2/6] Selecionando tenant..." -ForegroundColor Yellow
$selectBody = @{
    tenant_id = $tenant_id
} | ConvertTo-Json

$selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Headers @{
        "Content-Type"="application/json"
        "Authorization"="Bearer $token"
    } `
    -Body $selectBody

$finalToken = $selectResponse.access_token
Write-Host "   ✓ Tenant selecionado" -ForegroundColor Green

# Headers
$headers = @{
    "Authorization" = "Bearer $finalToken"
    "Content-Type" = "application/json"
}

# 3. Verificar Config WhatsApp
Write-Host "`n[3/6] Verificando config WhatsApp..." -ForegroundColor Yellow
try {
    $config = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config" `
        -Method GET `
        -Headers $headers
    Write-Host "   ✓ Config existe - Model: $($config.model_preference)" -ForegroundColor Green
} catch {
    Write-Host "   ⚠ Config não existe (criar com config_whatsapp_simples.ps1)" -ForegroundColor Yellow
}

# 4. Criar Agent (Atendente)
Write-Host "`n[4/6] Criando agent..." -ForegroundColor Yellow
$agentBody = @{
    name = "João Silva"
    email = "joao@petshop.com"
    status = "available"
    max_concurrent_chats = 5
} | ConvertTo-Json

try {
    $agent = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/agents" `
        -Method POST `
        -Headers $headers `
        -Body $agentBody
    Write-Host "   ✓ Agent criado: $($agent.name)" -ForegroundColor Green
    $agent_id = $agent.id
} catch {
    $errorDetail = $_.ErrorDetails.Message | ConvertFrom-Json
    if ($errorDetail.detail -like "*already exists*") {
        Write-Host "   ℹ Agent já existe, buscando..." -ForegroundColor Cyan
        $agents = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/agents" `
            -Method GET `
            -Headers $headers
        $agent = $agents | Where-Object { $_.email -eq "joao@petshop.com" } | Select-Object -First 1
        $agent_id = $agent.id
        Write-Host "   ✓ Agent encontrado: $($agent.name)" -ForegroundColor Green
    } else {
        throw
    }
}

# 5. Simular Mensagem com Sentimento Negativo
Write-Host "`n[5/6] Testando sentiment analysis..." -ForegroundColor Yellow
$testMessages = @(
    @{ text = "Oi, bom dia!" ; expected = "neutral" },
    @{ text = "Estou muito irritado com o atraso!" ; expected = "negative" },
    @{ text = "Isso é urgente, preciso falar com alguém AGORA!" ; expected = "negative" }
)

foreach ($msg in $testMessages) {
    Write-Host "   Testando: '$($msg.text)'" -ForegroundColor Gray
    
    # Aqui seria o webhook real, mas vamos simular
    $sentimentBody = @{
        message = $msg.text
    } | ConvertTo-Json
    
    try {
        # Endpoint de teste de sentiment (você vai criar)
        $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-sentiment" `
            -Method POST `
            -Headers $headers `
            -Body $sentimentBody
        
        Write-Host "     -> Score: $($result.score) | Emotion: $($result.emotion)" -ForegroundColor Cyan
        
        if ($result.should_handoff) {
            Write-Host "     -> Handoff necessario!" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "     -> Endpoint de teste nao existe ainda" -ForegroundColor Yellow
    }
}

# 6. Listar Handoffs Pendentes
Write-Host "`n[6/6] Verificando handoffs pendentes..." -ForegroundColor Yellow
try {
    $handoffs = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/handoffs?status=pending" `
        -Method GET `
        -Headers $headers
    
    Write-Host "   OK Total de handoffs pendentes: $($handoffs.Count)" -ForegroundColor Green
    
    if ($handoffs.Count -gt 0) {
        Write-Host "`n   Handoffs:" -ForegroundColor Cyan
        foreach ($h in $handoffs) {
            Write-Host "     - Sessao: $($h.session_id)" -ForegroundColor Gray
            Write-Host "       Prioridade: $($h.priority) | Status: $($h.status)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "   Endpoint de handoffs ainda nao criado" -ForegroundColor Yellow
}

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "  TESTE COMPLETO!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "`nProximo passo: Criar endpoints da API" -ForegroundColor Yellow
Write-Host "- POST /api/whatsapp/agents" -ForegroundColor Gray
Write-Host "- GET /api/whatsapp/handoffs" -ForegroundColor Gray
Write-Host "- POST /api/whatsapp/handoffs/:id/assign" -ForegroundColor Gray
Write-Host "- POST /api/whatsapp/test-sentiment" -ForegroundColor Gray
