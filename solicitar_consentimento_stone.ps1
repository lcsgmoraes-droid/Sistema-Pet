# Script para solicitar consentimento Stone
# Executa automaticamente: Login → Solicita Consentimento

param(
    [string]$Email = "admin@petshop.com",
    [string]$Senha = "admin123"
)

$ngrokUrl = "https://postdiscoidal-grouty-chandra.ngrok-free.dev"
$webhookUrl = "$ngrokUrl/api/stone/webhook-consentimento"
$baseUrl = "http://localhost:8000"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  SOLICITAÇÃO DE CONSENTIMENTO - STONE API" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Passo 1: Fazer login
Write-Host "[1/3] Fazendo login como admin..." -ForegroundColor Yellow

$loginBody = @{
    email = $Email
    password = $Senha
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login-multitenant" `
        -Method Post `
        -Body $loginBody `
        -ContentType "application/json"
    
    $token = $loginResponse.access_token
    $tenants = $loginResponse.tenants
    
    if ($tenants.Count -eq 0) {
        Write-Host "      ❌ Usuário não tem acesso a nenhum tenant!" -ForegroundColor Red
        exit 1
    }
    
    $tenantId = $tenants[0].id
    $tenantName = $tenants[0].name
    Write-Host "      ✅ Login realizado! Tenant: $tenantName" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "      ❌ Erro no login!" -ForegroundColor Red
    Write-Host "      $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Passo 2: Selecionar tenant
Write-Host "[2/3] Selecionando tenant..." -ForegroundColor Yellow

$selectTenantBody = @{
    tenant_id = $tenantId
} | ConvertTo-Json

try {
    $tenantResponse = Invoke-RestMethod -Uri "$baseUrl/auth/select-tenant" `
        -Method Post `
        -Body $selectTenantBody `
        -ContentType "application/json" `
        -Headers @{
            "Authorization" = "Bearer $token"
        }
    
    $finalToken = $tenantResponse.access_token
    Write-Host "      ✅ Tenant selecionado!" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "      ❌ Erro ao selecionar tenant!" -ForegroundColor Red
    Write-Host "      $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Passo 3: Solicitar consentimento
Write-Host "[3/3] Solicitando consentimento Stone..." -ForegroundColor Yellow
Write-Host ""
Write-Host "      CNPJ: 33590794000140" -ForegroundColor White
Write-Host "      Stone Code: 691890226" -ForegroundColor White
Write-Host "      Webhook: $webhookUrl" -ForegroundColor White
Write-Host ""

$consentBody = @{
    document = "33590794000140"
    affiliation_code = "691890226"
    webhook_url = $webhookUrl
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/stone/solicitar-consentimento" `
        -Method Post `
        -Body $consentBody `
        -ContentType "application/json" `
        -Headers @{
            "Authorization" = "Bearer $finalToken"
        }
    
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  ✅ SOLICITAÇÃO ENVIADA COM SUCESSO!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host ($response | ConvertTo-Json -Depth 5)
    Write-Host ""
    Write-Host "📧 PRÓXIMO PASSO:" -ForegroundColor Cyan
    Write-Host "   Verifique o email do titular da conta Stone" -ForegroundColor Yellow
    Write-Host "   (CNPJ: 33590794000140)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Quando o lojista aprovar, as credenciais" -ForegroundColor Yellow
    Write-Host "   serão enviadas automaticamente para o webhook." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   🔔 Mantenha o ngrok rodando para receber o webhook!" -ForegroundColor Magenta
    Write-Host ""
    
} catch {
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "  ❌ ERRO AO SOLICITAR CONSENTIMENTO" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    if ($_.ErrorDetails.Message) {
        try {
            Write-Host ($_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 5) -ForegroundColor Red
        } catch {
            Write-Host $_.ErrorDetails.Message -ForegroundColor Red
        }
    }
}
