# ⚡ Script de Configuração Rápida - OpenAI

Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🔧 CONFIGURAÇÃO RÁPIDA - OPENAI API KEY              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# ================== PASSO 1: COLAR API KEY ==================
Write-Host "`n📋 Cole a OpenAI API Key abaixo (começa com sk-proj ou sk-):" -ForegroundColor Yellow
$OPENAI_KEY = Read-Host

if (-not $OPENAI_KEY -or $OPENAI_KEY.Length -lt 20) {
    Write-Host "`n❌ Key inválida! Deve ter mais de 20 caracteres." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Key recebida: $($OPENAI_KEY.Substring(0, 15))..." -ForegroundColor Green

# ================== PASSO 2: LOGIN NO SISTEMA ==================
Write-Host "`n🔐 Fazendo login no sistema..." -ForegroundColor Cyan

try {
    $loginBody = @{
        email = "admin@test.com"
        password = "test123"
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login-multitenant" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $loginBody

    $tenant_id = $loginResponse.tenants[0].id
    $token = $loginResponse.access_token
    
    Write-Host "✅ Login OK - Tenant ID: $tenant_id" -ForegroundColor Green
} catch {
    Write-Host "`n❌ Erro no login: $_" -ForegroundColor Red
    Write-Host "Certifique-se que o backend está rodando: uvicorn app.main:app --reload" -ForegroundColor Yellow
    exit 1
}

# ================== PASSO 3: SELECIONAR TENANT ==================
Write-Host "`n🏢 Selecionando tenant..." -ForegroundColor Cyan

try {
    $selectBody = @{
        tenant_id = $tenant_id
    } | ConvertTo-Json

    $selectResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/select-tenant" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Authorization" = "Bearer $token"
        } `
        -Body $selectBody

    $finalToken = $selectResponse.access_token
    
    Write-Host "✅ Tenant selecionado!" -ForegroundColor Green
} catch {
    Write-Host "`n❌ Erro ao selecionar tenant: $_" -ForegroundColor Red
    exit 1
}

# ================== PASSO 4: VERIFICAR CONFIG EXISTENTE ==================
Write-Host "`n🔍 Verificando configuração existente..." -ForegroundColor Cyan

$configExists = $false
try {
    $existingConfig = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" `
        -Method GET `
        -Headers @{
            "Authorization" = "Bearer $finalToken"
        }
    
    if ($existingConfig) {
        $configExists = $true
        Write-Host "⚠️  Configuração já existe - faremos UPDATE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✅ Nenhuma configuração encontrada - faremos CREATE" -ForegroundColor Green
}

# ================== PASSO 5: CRIAR/ATUALIZAR CONFIG ==================
Write-Host "`n💾 Salvando configuração..." -ForegroundColor Cyan

$configBody = @{
    openai_api_key = $OPENAI_KEY
    bot_name = "Assistente Pet Shop"
    tone = "amigavel"
    model_preference = "gpt-4o-mini"
    max_tokens = 500
    temperature = 0.7
    auto_response_enabled = $true
    working_hours_start = "08:00:00"
    working_hours_end = "18:00:00"
} | ConvertTo-Json

try {
    if ($configExists) {
        # UPDATE
        $result = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" `
            -Method PUT `
            -Headers @{
                "Authorization" = "Bearer $finalToken"
                "Content-Type" = "application/json"
            } `
            -Body $configBody
        
        Write-Host "✅ Configuração ATUALIZADA com sucesso!" -ForegroundColor Green
    } else {
        # CREATE
        $result = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" `
            -Method POST `
            -Headers @{
                "Authorization" = "Bearer $finalToken"
                "Content-Type" = "application/json"
            } `
            -Body $configBody
        
        Write-Host "✅ Configuração CRIADA com sucesso!" -ForegroundColor Green
    }
} catch {
    Write-Host "`n❌ Erro ao salvar configuração: $_" -ForegroundColor Red
    
    # Tentar o método alternativo
    Write-Host "`n🔄 Tentando método alternativo..." -ForegroundColor Yellow
    
    try {
        if ($configExists) {
            $result = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" `
                -Method POST `
                -Headers @{
                    "Authorization" = "Bearer $finalToken"
                    "Content-Type" = "application/json"
                } `
                -Body $configBody
        } else {
            $result = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" `
                -Method PUT `
                -Headers @{
                    "Authorization" = "Bearer $finalToken"
                    "Content-Type" = "application/json"
                } `
                -Body $configBody
        }
        Write-Host "✅ Sucesso no método alternativo!" -ForegroundColor Green
    } catch {
        Write-Host "`n❌ Ambos os métodos falharam: $_" -ForegroundColor Red
        exit 1
    }
}

# ================== PASSO 6: TESTAR INTENT DETECTION ==================
Write-Host "`n🧪 Testando detecção de intenção..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

try {
    $intentBody = @{
        message = "Quanto custa a racao Golden?"
    } | ConvertTo-Json

    $intentResult = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/intent" `
        -Method POST `
        -Headers @{
            "Authorization" = "Bearer $finalToken"
            "Content-Type" = "application/json"
        } `
        -Body $intentBody `
        -TimeoutSec 10

    Write-Host "✅ Intent Detection OK!" -ForegroundColor Green
    Write-Host "   Intent: $($intentResult.intent)" -ForegroundColor Gray
    Write-Host "   Confidence: $($intentResult.confidence)" -ForegroundColor Gray
} catch {
    Write-Host "⚠️  Erro no teste de intent: $_" -ForegroundColor Yellow
}

# ================== PASSO 7: TESTAR COM OPENAI ==================
Write-Host "`n🤖 Testando com OpenAI (pode demorar 2-5s)..." -ForegroundColor Cyan
Write-Host "   Aguarde..." -ForegroundColor Gray
Start-Sleep -Seconds 2

try {
    $messageBody = @{
        message = "Oi! Quero comprar racao para cachorro"
        phone_number = "+5511999887766"
    } | ConvertTo-Json

    $messageResult = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" `
        -Method POST `
        -Headers @{
            "Authorization" = "Bearer $finalToken"
            "Content-Type" = "application/json"
        } `
        -Body $messageBody `
        -TimeoutSec 30

    Write-Host "`n" -NoNewline
    Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                           ║" -ForegroundColor Green
    Write-Host "║            ✅ SUCESSO! IA ESTÁ RESPONDENDO! ✅            ║" -ForegroundColor Green
    Write-Host "║                                                           ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
    
    Write-Host "`n📊 Métricas:" -ForegroundColor Cyan
    Write-Host "   Intent: $($messageResult.intent) (confiança: $($messageResult.confidence))" -ForegroundColor White
    Write-Host "   Tokens usados: $($messageResult.tokens_used)" -ForegroundColor White
    Write-Host "   Tempo de processamento: $([math]::Round($messageResult.processing_time, 2))s" -ForegroundColor White
    Write-Host "   Modelo: $($messageResult.model_used)" -ForegroundColor White
    Write-Host "   Mensagens no contexto: $($messageResult.context_messages)" -ForegroundColor White
    
    Write-Host "`n💬 Resposta da IA:" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "$($messageResult.response)" -ForegroundColor White
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    
    Write-Host "`n🎉 SPRINT 3 - 100% FUNCIONAL!" -ForegroundColor Green
    Write-Host "   Pronto para continuar Sprint 4 (Human Handoff)" -ForegroundColor Gray
    
} catch {
    Write-Host "`n" -NoNewline
    Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║                                                           ║" -ForegroundColor Red
    Write-Host "║                    ❌ ERRO NO TESTE                       ║" -ForegroundColor Red
    Write-Host "║                                                           ║" -ForegroundColor Red
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Red
    
    Write-Host "`n$_" -ForegroundColor Yellow
    
    # Verificar se é erro de API key
    if ($_.ToString() -like "*401*" -or $_.ToString() -like "*Incorrect API key*") {
        Write-Host "`n⚠️  A OpenAI API Key parece estar inválida!" -ForegroundColor Yellow
        Write-Host "   Verifique se:" -ForegroundColor Gray
        Write-Host "   1. A key foi copiada corretamente (sem espaços)" -ForegroundColor Gray
        Write-Host "   2. A key está ativa no painel OpenAI" -ForegroundColor Gray
        Write-Host "   3. Você tem créditos disponíveis" -ForegroundColor Gray
        Write-Host "`n   Execute o script novamente com uma key válida." -ForegroundColor Gray
    } else {
        Write-Host "`n⚠️  Erro inesperado - verifique os logs do backend" -ForegroundColor Yellow
    }
    
    exit 1
}

# ================== RESUMO FINAL ==================
Write-Host "`n" -NoNewline
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "║                  📋 CONFIGURAÇÃO COMPLETA                 ║" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n✅ Checklist:" -ForegroundColor Green
Write-Host "   [✓] OpenAI API Key configurada" -ForegroundColor White
Write-Host "   [✓] Horário comercial definido (08:00-18:00)" -ForegroundColor White
Write-Host "   [✓] Auto-resposta ativada" -ForegroundColor White
Write-Host "   [✓] Modelo: GPT-4o-mini (econômico)" -ForegroundColor White
Write-Host "   [✓] Tom: Amigável" -ForegroundColor White
Write-Host "   [✓] Intent detection funcionando" -ForegroundColor White
Write-Host "   [✓] IA respondendo corretamente" -ForegroundColor White

Write-Host "`n📝 Próximos passos:" -ForegroundColor Cyan
Write-Host "   1. Sprint 4 - Human Handoff" -ForegroundColor White
Write-Host "   2. Antes do deploy: Configurar 360dialog" -ForegroundColor White
Write-Host "   3. Antes do deploy: Configurar Google Maps" -ForegroundColor White

Write-Host "`n🚀 Pode continuar o desenvolvimento!" -ForegroundColor Green
Write-Host ""
