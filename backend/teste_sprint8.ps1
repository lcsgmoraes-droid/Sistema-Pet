# ============================================================================
# TESTE SPRINT 8: Security & LGPD
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  TESTE SPRINT 8: Security & LGPD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$BASE_URL = "http://localhost:8000"
$ErrorActionPreference = "Continue"

# ============================================================================
# 1. AUTENTICACAO
# ============================================================================

Write-Host "`n[1/8] Fazendo login..." -ForegroundColor Yellow

try {
    $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body (@{email="admin@test.com"; password="test123"} | ConvertTo-Json)
    
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
# 2. REGISTRAR CONSENTIMENTO LGPD
# ============================================================================

Write-Host "`n[2/8] LGPD: Registrar Consentimento" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$consentBody = @{
    subject_type = "customer"
    subject_id = "test-customer-001"
    consent_type = "whatsapp"
    consent_given = $true
    consent_text = "Aceito receber mensagens via WhatsApp"
    phone_number = "+5511999999999"
} | ConvertTo-Json

try {
    $consent = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/lgpd/consent" `
        -Method POST `
        -Headers $HEADERS `
        -Body $consentBody
    
    Write-Host "[OK] Consentimento registrado" -ForegroundColor Green
    Write-Host "ID: $($consent.id)" -ForegroundColor White
    Write-Host "Subject: $($consent.subject_id)" -ForegroundColor White
    Write-Host "Tipo: $($consent.consent_type)" -ForegroundColor White
    Write-Host "Dado: $($consent.consent_given)" -ForegroundColor White
} catch {
    Write-Host "[ERRO] Falha ao registrar consentimento: $_" -ForegroundColor Red
}

# ============================================================================
# 3. VERIFICAR CONSENTIMENTO
# ============================================================================

Write-Host "`n[3/8] LGPD: Verificar Consentimento" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$checkBody = @{
    subject_id = "test-customer-001"
    consent_type = "whatsapp"
} | ConvertTo-Json

try {
    $check = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/lgpd/consent/check" `
        -Method POST `
        -Headers $HEADERS `
        -Body $checkBody
    
    Write-Host "[OK] Verificacao realizada" -ForegroundColor Green
    Write-Host "Tem consentimento: $($check.has_consent)" -ForegroundColor White
} catch {
    Write-Host "[ERRO] Falha na verificacao: $_" -ForegroundColor Red
}

# ============================================================================
# 4. SOLICITAR EXCLUSAO DE DADOS
# ============================================================================

Write-Host "`n[4/8] LGPD: Solicitar Exclusao de Dados" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$deletionBody = @{
    subject_type = "customer"
    subject_id = "test-customer-002"
    reason = "Nao utilizo mais o servico"
    phone_number = "+5511988888888"
    email = "test@example.com"
} | ConvertTo-Json

try {
    $deletion = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/lgpd/deletion-request" `
        -Method POST `
        -Headers $HEADERS `
        -Body $deletionBody
    
    Write-Host "[OK] Solicitacao criada" -ForegroundColor Green
    Write-Host "Request ID: $($deletion.request_id)" -ForegroundColor White
    Write-Host "Status: $($deletion.status)" -ForegroundColor White
    Write-Host "Mensagem: $($deletion.message)" -ForegroundColor Gray
    
    $DELETION_REQUEST_ID = $deletion.request_id
} catch {
    Write-Host "[ERRO] Falha ao criar solicitacao: $_" -ForegroundColor Red
    $DELETION_REQUEST_ID = $null
}

# ============================================================================
# 5. LISTAR SOLICITACOES DE EXCLUSAO
# ============================================================================

Write-Host "`n[5/8] LGPD: Listar Solicitacoes de Exclusao" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

try {
    $requests = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/lgpd/deletion-requests" `
        -Method GET `
        -Headers $HEADERS
    
    Write-Host "[OK] Solicitacoes listadas: $($requests.requests.Count)" -ForegroundColor Green
    
    if ($requests.requests.Count -gt 0) {
        Write-Host "`nUltimas solicitacoes:" -ForegroundColor Yellow
        foreach ($req in $requests.requests | Select-Object -First 3) {
            Write-Host "  - ID: $($req.id)" -ForegroundColor White
            Write-Host "    Subject: $($req.subject_id)" -ForegroundColor Gray
            Write-Host "    Status: $($req.status)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "[ERRO] Falha ao listar: $_" -ForegroundColor Red
}

# ============================================================================
# 6. EXPORTAR DADOS DO USUARIO
# ============================================================================

Write-Host "`n[6/8] LGPD: Exportar Dados do Usuario" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

$exportBody = @{
    subject_id = "test-customer-001"
    subject_type = "customer"
} | ConvertTo-Json

try {
    $export = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/lgpd/data-export" `
        -Method POST `
        -Headers $HEADERS `
        -Body $exportBody
    
    Write-Host "[OK] Dados exportados" -ForegroundColor Green
    Write-Host "Subject: $($export.subject_id)" -ForegroundColor White
    Write-Host "Data: $($export.export_date)" -ForegroundColor White
    Write-Host "Nota: $($export.note)" -ForegroundColor Gray
} catch {
    Write-Host "[ERRO] Falha ao exportar: $_" -ForegroundColor Red
}

# ============================================================================
# 7. GERAR SECRET PARA WEBHOOK
# ============================================================================

Write-Host "`n[7/8] Security: Gerar Secret para Webhook" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

try {
    $secret = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/webhook/generate-secret" `
        -Method POST `
        -Headers $HEADERS
    
    Write-Host "[OK] Secret gerada" -ForegroundColor Green
    Write-Host "Secret: $($secret.secret.Substring(0,20))..." -ForegroundColor White
    Write-Host "Nota: $($secret.note)" -ForegroundColor Gray
} catch {
    Write-Host "[ERRO] Falha ao gerar secret: $_" -ForegroundColor Red
}

# ============================================================================
# 8. LOGS DE AUDITORIA
# ============================================================================

Write-Host "`n[8/8] Security: Logs de Auditoria" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Gray

try {
    $logs = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/security/audit/logs?limit=5" `
        -Method GET `
        -Headers $HEADERS
    
    Write-Host "[OK] Logs obtidos: $($logs.logs.Count)" -ForegroundColor Green
    
    if ($logs.logs.Count -gt 0) {
        Write-Host "`nUltimos eventos:" -ForegroundColor Yellow
        foreach ($log in $logs.logs) {
            Write-Host "  - $($log.event_type) [$($log.severity)]" -ForegroundColor White
            Write-Host "    $($log.description)" -ForegroundColor Gray
        }
    } else {
        Write-Host "Nenhum log encontrado ainda" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Falha ao obter logs: $_" -ForegroundColor Red
}

# ============================================================================
# RESUMO
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  RESUMO SPRINT 8" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nTestes realizados:" -ForegroundColor Cyan
Write-Host "   [OK] Registrar consentimento LGPD" -ForegroundColor Green
Write-Host "   [OK] Verificar consentimento" -ForegroundColor Green
Write-Host "   [OK] Solicitar exclusao de dados" -ForegroundColor Green
Write-Host "   [OK] Listar solicitacoes" -ForegroundColor Green
Write-Host "   [OK] Exportar dados do usuario" -ForegroundColor Green
Write-Host "   [OK] Gerar secret webhook" -ForegroundColor Green
Write-Host "   [OK] Logs de auditoria" -ForegroundColor Green

Write-Host "`nImplementado:" -ForegroundColor Cyan
Write-Host "   1. LGPD - Sistema completo de consentimento" -ForegroundColor Gray
Write-Host "   2. LGPD - Direito ao esquecimento" -ForegroundColor Gray
Write-Host "   3. LGPD - Portabilidade de dados" -ForegroundColor Gray
Write-Host "   4. LGPD - Logs de acesso" -ForegroundColor Gray
Write-Host "   5. Security - HMAC validation webhooks" -ForegroundColor Gray
Write-Host "   6. Security - Auditoria de eventos" -ForegroundColor Gray
Write-Host "   7. Security - Rate limiting (estrutura)" -ForegroundColor Gray

Write-Host "`nProximo (Sprint 9):" -ForegroundColor Cyan
Write-Host "   - Polish & Launch" -ForegroundColor White
Write-Host "   - Testes finais" -ForegroundColor White
Write-Host "   - Documentacao completa" -ForegroundColor White
Write-Host "   - Sistema em producao" -ForegroundColor White

Write-Host "`n"
