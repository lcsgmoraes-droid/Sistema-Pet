# Configuração Simplificada WhatsApp + IA
# Executa configuração passo a passo

$BASE_URL = "http://localhost:8000"
$OPENAI_KEY = "sk-proj-U5ClBgQjRpnJ3xCAmXlyshqjXbU-hePvydc61GHZ0QZo9mlVf7Kbi5JVpTcNSV6--J5jJsdWxqT3BlbkFJ76jgPB8VuHZ6kJRTSpF1j_8-gxojKj761rFXAts8ZSQIPhmKBjzbhDghDZ54TjEhl0rhR4ikA"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACAO WHATSAPP + IA" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Passo 1: Login
Write-Host "[1/4] Login..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@test.com"
    password = "admin123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $loginBody

$token = $loginResponse.access_token
Write-Host "OK - Token obtido" -ForegroundColor Green

# Passo 2: Selecionar Tenant
Write-Host "`n[2/4] Selecionando tenant..." -ForegroundColor Yellow
$tenant = $loginResponse.tenants[0]
$tenant_id = $tenant.id
$tenant_name = $tenant.name
Write-Host "Tenant: $tenant_name ($tenant_id)" -ForegroundColor Gray

$selectBody = @{ tenant_id = $tenant_id } | ConvertTo-Json
$selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
    -Method POST `
    -Headers @{
        "Content-Type"="application/json"
        "Authorization"="Bearer $token"
    } `
    -Body $selectBody

$finalToken = $selectResponse.access_token
Write-Host "OK - Tenant selecionado" -ForegroundColor Green

# Passo 3: DELETE config antiga (se existir) + POST nova
Write-Host "`n[3/5] Removendo configuracao antiga (se existir)..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config" `
        -Method DELETE `
        -Headers @{"Authorization"="Bearer $finalToken"} | Out-Null
    Write-Host "OK - Config antiga removida" -ForegroundColor Green
} catch {
    Write-Host "Sem config anterior (normal)" -ForegroundColor Gray
}

Start-Sleep -Seconds 1

Write-Host "`n[4/5] Salvando NOVA configuracao WhatsApp + IA..." -ForegroundColor Yellow
$configBody = @{
    provider = "360dialog"
    openai_api_key = $OPENAI_KEY
    model_preference = "gpt-4o-mini"
    auto_response_enabled = $true
    bot_name = "Assistente Pet Shop"
    greeting_message = "Ola! Sou o assistente virtual. Como posso ajudar?"
    tone = "friendly"
} | ConvertTo-Json

try {
    $configResponse = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config" `
        -Method POST `
        -Headers @{
            "Content-Type"="application/json"
            "Authorization"="Bearer $finalToken"
        } `
        -Body $configBody
    
    Write-Host "OK - Configuracao salva!" -ForegroundColor Green
    Write-Host "ID: $($configResponse.id)" -ForegroundColor Gray
} catch {
    Write-Host "ERRO ao salvar configuracao:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Passo 4: GET Stats
Write-Host "`n[5/5] Buscando estatisticas..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config/stats" `
        -Method GET `
        -Headers @{"Authorization"="Bearer $finalToken"}
    
    Write-Host "OK - Stats obtidas" -ForegroundColor Green
    Write-Host "Sessoes: $($stats.total_sessions)" -ForegroundColor Gray
    Write-Host "Mensagens: $($stats.total_messages)" -ForegroundColor Gray
} catch {
    Write-Host "AVISO: Stats nao disponiveis ainda" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACAO CONCLUIDA COM SUCESSO!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan
