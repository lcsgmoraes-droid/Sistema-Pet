# ============================================================================
# TESTE COMPLETO - SPRINT 6: Tool Calling + IA Service
# ============================================================================

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🧪 TESTE SPRINT 6: Tool Calling + IA                   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

$BASE_URL = "http://localhost:8000"
$ErrorActionPreference = "Continue"

# ============================================================================
# 1. AUTENTICAÇÃO
# ============================================================================

Write-Host "`n🔐 Fazendo login..." -ForegroundColor Yellow

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
    Write-Host "✅ Login OK" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro no login: $_" -ForegroundColor Red
    exit 1
}

$HEADERS = @{
    "Authorization" = "Bearer $TOKEN"
    "Content-Type" = "application/json"
}

# ============================================================================
# 2. LISTAR TOOLS DISPONÍVEIS
# ============================================================================

Write-Host "`n📋 TESTE 1: Listar Tools Disponíveis" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $tools = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/tools" -Method GET -Headers $HEADERS
    
    Write-Host "✅ $($tools.total) tools encontradas:" -ForegroundColor Green
    foreach ($tool in $tools.tools) {
        Write-Host "   • $($tool.name)" -ForegroundColor White
        Write-Host "     $($tool.description)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

# ============================================================================
# 3. TESTAR TOOL: BUSCAR PRODUTOS
# ============================================================================

Write-Host "`n📦 TESTE 2: Tool - Buscar Produtos" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $testPayload = @{
        tool_name = "buscar_produtos"
        arguments = @{
            query = "ração golden"
            limite = 3
        }
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-tool" `
        -Method POST -Headers $HEADERS -Body $testPayload
    
    if ($result.success) {
        Write-Host "✅ Tool executada com sucesso!" -ForegroundColor Green
        Write-Host "   Produtos encontrados: $($result.result.total)" -ForegroundColor Cyan
        
        if ($result.result.produtos) {
            foreach ($produto in $result.result.produtos) {
                Write-Host "   • $($produto.nome) - R$ $($produto.preco)" -ForegroundColor White
            }
        }
    } else {
        Write-Host "❌ Erro na tool: $($result.result.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

# ============================================================================
# 4. TESTAR TOOL: VERIFICAR HORÁRIOS
# ============================================================================

Write-Host "`n⏰ TESTE 3: Tool - Verificar Horários" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $testPayload = @{
        tool_name = "verificar_horarios_disponiveis"
        arguments = @{
            tipo_servico = "banho"
            data = "amanha"
        }
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-tool" `
        -Method POST -Headers $HEADERS -Body $testPayload
    
    if ($result.success) {
        Write-Host "✅ Horários disponíveis:" -ForegroundColor Green
        Write-Host "   Data: $($result.result.data)" -ForegroundColor Cyan
        Write-Host "   Horários: $($result.result.horarios_disponiveis -join ', ')" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

# ============================================================================
# 5. TESTAR TOOL: CRIAR AGENDAMENTO
# ============================================================================

Write-Host "`n📅 TESTE 4: Tool - Criar Agendamento" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $dataAmanha = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
    
    $testPayload = @{
        tool_name = "criar_agendamento"
        arguments = @{
            tipo_servico = "banho"
            data = $dataAmanha
            horario = "14:00"
            nome_pet = "Rex"
            observacoes = "Pet de grande porte"
        }
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-tool" `
        -Method POST -Headers $HEADERS -Body $testPayload
    
    if ($result.success) {
        Write-Host "✅ Agendamento criado!" -ForegroundColor Green
        Write-Host "   Código: $($result.result.codigo)" -ForegroundColor Cyan
        Write-Host "   $($result.result.message)" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

# ============================================================================
# 6. TESTE DE MENSAGEM COM IA
# ============================================================================

Write-Host "`n🤖 TESTE 5: Mensagem Completa com IA" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $testPayload = @{
        message = "Tem ração Golden?"
        phone_number = "5511999999999"
    } | ConvertTo-Json
    
    Write-Host "Enviando: 'Tem ração Golden?'" -ForegroundColor Yellow
    
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-message" `
        -Method POST -Headers $HEADERS -Body $testPayload
    
    if ($result.success) {
        Write-Host "`n✅ IA respondeu!" -ForegroundColor Green
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
        Write-Host $result.response -ForegroundColor White
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
        Write-Host "`n📊 Métricas:" -ForegroundColor Cyan
        Write-Host "   Intent: $($result.intent)" -ForegroundColor Gray
        Write-Host "   Confidence: $($result.confidence)" -ForegroundColor Gray
        Write-Host "   Tempo: $([math]::Round($result.processing_time, 2))s" -ForegroundColor Gray
        Write-Host "   Tokens: $($result.tokens_used)" -ForegroundColor Gray
        Write-Host "   Model: $($result.model_used)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Erro: $($result.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

# ============================================================================
# 7. TESTE DE CONVERSAÇÃO COMPLETA
# ============================================================================

Write-Host "`n💬 TESTE 6: Conversação Completa" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $testPayload = @{
        messages = @(
            "Olá!",
            "Tem ração Golden?",
            "Quero agendar banho para meu cachorro"
        )
        phone_number = "5511999999999"
    } | ConvertTo-Json
    
    Write-Host "Simulando conversa com 3 mensagens..." -ForegroundColor Yellow
    
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-conversation" `
        -Method POST -Headers $HEADERS -Body $testPayload
    
    if ($result.success) {
        Write-Host "`n✅ Conversação completa!" -ForegroundColor Green
        
        foreach ($turn in $result.conversation) {
            Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
            Write-Host "👤 Cliente: $($turn.user)" -ForegroundColor Cyan
            Write-Host "🤖 IA: $($turn.assistant)" -ForegroundColor Green
            Write-Host "   Intent: $($turn.intent) | Tools: $($turn.tool_calls)" -ForegroundColor Gray
        }
        
        Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

# ============================================================================
# RESUMO FINAL
# ============================================================================

Write-Host "`n`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ SPRINT 6: TESTE COMPLETO                            ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n✅ Funcionalidades Testadas:" -ForegroundColor White
Write-Host "   1. Listagem de tools disponíveis" -ForegroundColor Gray
Write-Host "   2. Execução individual de tools" -ForegroundColor Gray
Write-Host "   3. Integração com IA Service" -ForegroundColor Gray
Write-Host "   4. Tool calling automático" -ForegroundColor Gray
Write-Host "   5. Conversação completa" -ForegroundColor Gray

Write-Host "`n🎯 Próximos Passos:" -ForegroundColor Cyan
Write-Host "   • Integrar com sistemas reais (produtos, agendamentos)" -ForegroundColor White
Write-Host "   • Implementar Celery para notificações" -ForegroundColor White
Write-Host "   • Adicionar mais tools conforme necessidade" -ForegroundColor White

Write-Host "`n"
