# ============================================================================
# TESTE COMPLETO - SPRINT 6: Tool Calling + IA Service
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  TESTE SPRINT 6: Tool Calling + IA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$BASE_URL = "http://localhost:8000"
$ErrorActionPreference = "Continue"

# ============================================================================
# 1. AUTENTICACAO
# ============================================================================

Write-Host "`nFazendo login..." -ForegroundColor Yellow

try {
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
    
    $TOKEN = $selectResponse.access_token
    Write-Host "[OK] Login realizado" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Falha no login: $_" -ForegroundColor Red
    exit 1
}

$HEADERS = @{
    "Authorization" = "Bearer $TOKEN"
    "Content-Type" = "application/json"
}

# ============================================================================
# 2. LISTAR TOOLS DISPONIVEIS
# ============================================================================

Write-Host "`nTESTE 1: Listar Tools Disponiveis" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

try {
    $tools = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/tools" -Method GET -Headers $HEADERS
    
    Write-Host "[OK] Tools carregadas: $($tools.Count)" -ForegroundColor Green
    
    foreach ($tool in $tools) {
        Write-Host "  - $($tool.name): $($tool.description)" -ForegroundColor White
    }
} catch {
    Write-Host "[ERRO] Falha ao listar tools: $_" -ForegroundColor Red
}

# ============================================================================
# 3. TESTAR TOOL CALLING - BUSCAR PRODUTOS
# ============================================================================

Write-Host "`nTESTE 2: Buscar Produtos (Tool Calling)" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$testMessage = @{
    phone_number = "+5511999999999"
    message = "Tem racao Golden?"
    contact_name = "Teste User"
} | ConvertTo-Json

try {
    Write-Host "Enviando mensagem: 'Tem racao Golden?'" -ForegroundColor Yellow
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/webhook" `
        -Method POST `
        -Headers $HEADERS `
        -Body $testMessage
    
    Write-Host "[OK] Resposta recebida" -ForegroundColor Green
    Write-Host "Resposta da IA:" -ForegroundColor Cyan
    Write-Host $response.reply -ForegroundColor White
    
    if ($response.tools_used) {
        Write-Host "`nTools utilizadas:" -ForegroundColor Yellow
        foreach ($tool in $response.tools_used) {
            Write-Host "  - $tool" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "[ERRO] Falha no tool calling: $_" -ForegroundColor Red
}

# ============================================================================
# 4. TESTAR AGENDAMENTO
# ============================================================================

Write-Host "`nTESTE 3: Agendar Servico (Tool Calling)" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$agendamentoMsg = @{
    phone_number = "+5511999999999"
    message = "Quero agendar banho para meu cachorro amanha as 14h"
    contact_name = "Teste User"
} | ConvertTo-Json

try {
    Write-Host "Enviando: 'Quero agendar banho para meu cachorro amanha as 14h'" -ForegroundColor Yellow
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/webhook" `
        -Method POST `
        -Headers $HEADERS `
        -Body $agendamentoMsg
    
    Write-Host "[OK] Resposta recebida" -ForegroundColor Green
    Write-Host "Resposta da IA:" -ForegroundColor Cyan
    Write-Host $response.reply -ForegroundColor White
    
    if ($response.tools_used) {
        Write-Host "`nTools utilizadas:" -ForegroundColor Yellow
        foreach ($tool in $response.tools_used) {
            Write-Host "  - $tool" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "[ERRO] Falha no agendamento: $_" -ForegroundColor Red
}

# ============================================================================
# 5. TESTAR RASTREIO DE PEDIDO
# ============================================================================

Write-Host "`nTESTE 4: Rastrear Pedido (Tool Calling)" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$rastreioMsg = @{
    phone_number = "+5511999999999"
    message = "Onde esta meu pedido #12345?"
    contact_name = "Teste User"
} | ConvertTo-Json

try {
    Write-Host "Enviando: 'Onde esta meu pedido #12345?'" -ForegroundColor Yellow
    
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/webhook" `
        -Method POST `
        -Headers $HEADERS `
        -Body $rastreioMsg
    
    Write-Host "[OK] Resposta recebida" -ForegroundColor Green
    Write-Host "Resposta da IA:" -ForegroundColor Cyan
    Write-Host $response.reply -ForegroundColor White
    
    if ($response.tools_used) {
        Write-Host "`nTools utilizadas:" -ForegroundColor Yellow
        foreach ($tool in $response.tools_used) {
            Write-Host "  - $tool" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "[ERRO] Falha no rastreio: $_" -ForegroundColor Red
}

# ============================================================================
# 6. VERIFICAR METRICAS
# ============================================================================

Write-Host "`nTESTE 5: Verificar Metricas" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

try {
    $stats = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config/stats" -Method GET -Headers $HEADERS
    
    Write-Host "[OK] Metricas obtidas" -ForegroundColor Green
    Write-Host "Total de sessoes: $($stats.total_sessions)" -ForegroundColor White
    Write-Host "Total de mensagens: $($stats.total_messages)" -ForegroundColor White
    Write-Host "Total de handoffs: $($stats.total_handoffs)" -ForegroundColor White
    Write-Host "Custo total: R$ $($stats.total_cost)" -ForegroundColor White
    
    if ($stats.tool_usage) {
        Write-Host "`nUso de Tools:" -ForegroundColor Yellow
        foreach ($tool in $stats.tool_usage.PSObject.Properties) {
            Write-Host "  - $($tool.Name): $($tool.Value) vezes" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "[ERRO] Falha ao obter metricas: $_" -ForegroundColor Red
}

# ============================================================================
# RESUMO
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  RESUMO SPRINT 6" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nImplementado:" -ForegroundColor Cyan
Write-Host "   1. Sistema de tools registrado" -ForegroundColor Gray
Write-Host "   2. IA detecta quando usar tools" -ForegroundColor Gray
Write-Host "   3. Busca de produtos funcionando" -ForegroundColor Gray
Write-Host "   4. Tool calling automatico" -ForegroundColor Gray
Write-Host "   5. Conversacao completa" -ForegroundColor Gray

Write-Host "`nProximos Passos:" -ForegroundColor Cyan
Write-Host "   - Integrar com sistemas reais (produtos, agendamentos)" -ForegroundColor White
Write-Host "   - Implementar Celery para notificacoes" -ForegroundColor White
Write-Host "   - Adicionar mais tools conforme necessidade" -ForegroundColor White

Write-Host "`n"
