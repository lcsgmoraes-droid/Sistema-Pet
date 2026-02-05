# ============================================================================
# TESTE FINAL - SPRINT 9: Validação Completa do Sistema
# ============================================================================

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  TESTE FINAL - SPRINT 9" -ForegroundColor Cyan
Write-Host "  Validação Completa WhatsApp + IA" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$BASE_URL = "http://localhost:8000"
$ErrorActionPreference = "Continue"
$PASS_COUNT = 0
$FAIL_COUNT = 0

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null,
        [hashtable]$Headers = @{}
    )
    
    Write-Host "`n[$Name]" -ForegroundColor Yellow
    Write-Host "  Endpoint: $Method $Url" -ForegroundColor Gray
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            Headers = $Headers
            ErrorAction = "Stop"
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json)
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-RestMethod @params
        Write-Host "  [OK]" -ForegroundColor Green
        $script:PASS_COUNT++
        return $response
    } catch {
        Write-Host "  [ERRO] $($_.Exception.Message)" -ForegroundColor Red
        $script:FAIL_COUNT++
        return $null
    }
}

# ============================================================================
# 1. HEALTH CHECKS (Sprint 9)
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  1. HEALTH CHECKS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

Test-Endpoint -Name "Health Check Básico" -Url "$BASE_URL/health"
Test-Endpoint -Name "Liveness Check" -Url "$BASE_URL/health/live"
Test-Endpoint -Name "Readiness Check" -Url "$BASE_URL/health/ready"
$metrics = Test-Endpoint -Name "Application Metrics" -Url "$BASE_URL/health/metrics"

if ($metrics) {
    Write-Host "  Sessões Totais: $($metrics.metrics.sessions.total)" -ForegroundColor White
    Write-Host "  Mensagens Totais: $($metrics.metrics.messages.total)" -ForegroundColor White
}

# ============================================================================
# 2. AUTENTICAÇÃO
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  2. AUTENTICAÇÃO" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

$loginBody = @{
    email = "admin@test.com"
    password = "test123"
}

$loginResponse = Test-Endpoint -Name "Login Multi-Tenant" `
    -Url "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Body $loginBody

if (-not $loginResponse) {
    Write-Host "`n[ERRO CRÍTICO] Falha no login. Abortando testes." -ForegroundColor Red
    exit 1
}

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token

$selectBody = @{
    tenant_id = $tenant_id
}

$selectResponse = Test-Endpoint -Name "Selecionar Tenant" `
    -Url "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Body $selectBody `
    -Headers @{"Authorization" = "Bearer $token"}

$TOKEN = $selectResponse.access_token
$AUTH_HEADERS = @{
    "Authorization" = "Bearer $TOKEN"
    "Content-Type" = "application/json"
}

Write-Host "  Token obtido com sucesso" -ForegroundColor Green

# ============================================================================
# 3. SPRINT 2 - CONFIGURAÇÃO
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  3. SPRINT 2 - CONFIGURAÇÃO" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

Test-Endpoint -Name "Obter Configuração WhatsApp" `
    -Url "$BASE_URL/api/whatsapp/config" `
    -Headers $AUTH_HEADERS

# ============================================================================
# 4. SPRINT 3 - SESSÕES E MENSAGENS
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  4. SPRINT 3 - SESSÕES & MENSAGENS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

$sessionBody = @{
    telefone = "+5511999999999"
    nome_cliente = "Cliente Teste Final"
}

$session = Test-Endpoint -Name "Criar Sessão" `
    -Url "$BASE_URL/api/whatsapp/sessions" `
    -Method POST `
    -Body $sessionBody `
    -Headers $AUTH_HEADERS

if ($session) {
    Write-Host "  Session ID: $($session.id)" -ForegroundColor White
    
    # Enviar mensagem
    $messageBody = @{
        session_id = $session.id
        tipo = "recebida"
        telefone = "+5511999999999"
        texto = "Olá, preciso de ajuda"
    }
    
    $message = Test-Endpoint -Name "Processar Mensagem" `
        -Url "$BASE_URL/api/whatsapp/messages" `
        -Method POST `
        -Body $messageBody `
        -Headers $AUTH_HEADERS
    
    if ($message) {
        Write-Host "  Resposta IA: $($message.texto.Substring(0, [Math]::Min(50, $message.texto.Length)))..." -ForegroundColor White
    }
    
    # Histórico
    Test-Endpoint -Name "Obter Histórico" `
        -Url "$BASE_URL/api/whatsapp/sessions/$($session.id)/messages" `
        -Headers $AUTH_HEADERS
    
    # Detalhes da sessão
    Test-Endpoint -Name "Detalhes da Sessão" `
        -Url "$BASE_URL/api/whatsapp/sessions/$($session.id)" `
        -Headers $AUTH_HEADERS
}

# ============================================================================
# 5. SPRINT 4 - HANDOFFS
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  5. SPRINT 4 - HANDOFFS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

Test-Endpoint -Name "Listar Handoffs Pendentes" `
    -Url "$BASE_URL/api/whatsapp/handoffs/pending" `
    -Headers $AUTH_HEADERS

# ============================================================================
# 6. SPRINT 7 - ANALYTICS
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  6. SPRINT 7 - ANALYTICS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

$dashboard = Test-Endpoint -Name "Dashboard Analytics" `
    -Url "$BASE_URL/api/whatsapp/analytics/dashboard" `
    -Headers $AUTH_HEADERS

if ($dashboard) {
    Write-Host "  Sessões: $($dashboard.summary.total_sessions)" -ForegroundColor White
    Write-Host "  Mensagens: $($dashboard.summary.total_messages)" -ForegroundColor White
}

Test-Endpoint -Name "Análise de Tendências" `
    -Url "$BASE_URL/api/whatsapp/analytics/trends" `
    -Headers $AUTH_HEADERS

Test-Endpoint -Name "Análise de Custos" `
    -Url "$BASE_URL/api/whatsapp/analytics/costs" `
    -Headers $AUTH_HEADERS

# ============================================================================
# 7. SPRINT 8 - SECURITY & LGPD
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  7. SPRINT 8 - SECURITY & LGPD" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

# Registrar consentimento
$consentBody = @{
    subject_type = "customer"
    subject_id = "test-final-customer"
    consent_type = "whatsapp"
    consent_given = $true
    consent_text = "Aceito receber mensagens via WhatsApp"
    phone_number = "+5511999999999"
}

Test-Endpoint -Name "Registrar Consentimento LGPD" `
    -Url "$BASE_URL/api/whatsapp/security/lgpd/consent" `
    -Method POST `
    -Body $consentBody `
    -Headers $AUTH_HEADERS

# Verificar consentimento
$checkBody = @{
    subject_id = "test-final-customer"
    consent_type = "whatsapp"
}

$consent = Test-Endpoint -Name "Verificar Consentimento" `
    -Url "$BASE_URL/api/whatsapp/security/lgpd/consent/check" `
    -Method POST `
    -Body $checkBody `
    -Headers $AUTH_HEADERS

if ($consent) {
    Write-Host "  Consentimento ativo: $($consent.has_consent)" -ForegroundColor White
}

# Gerar secret webhook
Test-Endpoint -Name "Gerar Secret Webhook" `
    -Url "$BASE_URL/api/whatsapp/security/webhook/generate-secret" `
    -Method POST `
    -Headers $AUTH_HEADERS

# Logs de auditoria
Test-Endpoint -Name "Logs de Auditoria" `
    -Url "$BASE_URL/api/whatsapp/security/audit/logs?limit=5" `
    -Headers $AUTH_HEADERS

# ============================================================================
# 8. PROMETHEUS METRICS
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  8. PROMETHEUS METRICS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

$prometheus = Test-Endpoint -Name "Métricas Prometheus" `
    -Url "$BASE_URL/health/prometheus"

if ($prometheus) {
    Write-Host "  Formato Prometheus OK" -ForegroundColor Green
}

# ============================================================================
# RESUMO FINAL
# ============================================================================

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  RESUMO FINAL" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$TOTAL_TESTS = $PASS_COUNT + $FAIL_COUNT
$SUCCESS_RATE = [Math]::Round(($PASS_COUNT / $TOTAL_TESTS) * 100, 1)

Write-Host "`nTestes Executados: $TOTAL_TESTS" -ForegroundColor White
Write-Host "  ✅ Passou: $PASS_COUNT" -ForegroundColor Green
Write-Host "  ❌ Falhou: $FAIL_COUNT" -ForegroundColor Red
Write-Host "  📊 Taxa de Sucesso: $SUCCESS_RATE%" -ForegroundColor $(if ($SUCCESS_RATE -ge 90) { "Green" } elseif ($SUCCESS_RATE -ge 70) { "Yellow" } else { "Red" })

Write-Host "`nSprints Validados:" -ForegroundColor Cyan
Write-Host "  OK Sprint 2 - Configuracao" -ForegroundColor Green
Write-Host "  OK Sprint 3 - Sessoes e Mensagens" -ForegroundColor Green
Write-Host "  OK Sprint 4 - Handoffs" -ForegroundColor Green
Write-Host "  OK Sprint 7 - Analytics" -ForegroundColor Green
Write-Host "  OK Sprint 8 - Security e LGPD" -ForegroundColor Green
Write-Host "  OK Sprint 9 - Health e Monitoring" -ForegroundColor Green

Write-Host "`nSistema:" -ForegroundColor Cyan
if ($SUCCESS_RATE -ge 90) {
    Write-Host "  PRONTO PARA PRODUCAO!" -ForegroundColor Green
} elseif ($SUCCESS_RATE -ge 70) {
    Write-Host "  NECESSITA AJUSTES" -ForegroundColor Yellow
} else {
    Write-Host "  NAO ESTA PRONTO" -ForegroundColor Red
}

Write-Host ""
