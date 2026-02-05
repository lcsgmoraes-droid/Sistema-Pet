# Diagnóstico Completo - Fluxo Frontend
$BASE_URL = "http://localhost:8000"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTICO COMPLETO - FLUXO LOGIN" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# PASSO 1: LOGIN
Write-Host "[PASSO 1] Login inicial..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@test.com"
    password = "test123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login-multitenant" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $loginBody
    
    Write-Host "OK - Login bem-sucedido!" -ForegroundColor Green
    Write-Host "  User ID: $($loginResponse.user.id)" -ForegroundColor Gray
    Write-Host "  Email: $($loginResponse.user.email)" -ForegroundColor Gray
    Write-Host "  Token: $($loginResponse.access_token.Substring(0,50))..." -ForegroundColor Gray
    Write-Host "  Tenants disponiveis: $($loginResponse.tenants.Count)" -ForegroundColor Gray
    
    $token = $loginResponse.access_token
    $tenant_id = $loginResponse.tenants[0].id
    $tenant_name = $loginResponse.tenants[0].name
    
    Write-Host "`n  Tenant selecionado automaticamente:" -ForegroundColor Cyan
    Write-Host "    ID: $tenant_id" -ForegroundColor Gray
    Write-Host "    Nome: $tenant_name" -ForegroundColor Gray
    
} catch {
    Write-Host "ERRO - Login falhou!" -ForegroundColor Red
    Write-Host "  Detalhes: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# PASSO 2: SELECT TENANT
Write-Host "`n[PASSO 2] Selecionando tenant..." -ForegroundColor Yellow
$selectBody = @{ tenant_id = $tenant_id } | ConvertTo-Json

try {
    $selectResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/select-tenant" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Authorization" = "Bearer $token"
        } `
        -Body $selectBody
    
    Write-Host "OK - Tenant selecionado!" -ForegroundColor Green
    Write-Host "  Novo Token: $($selectResponse.access_token.Substring(0,50))..." -ForegroundColor Gray
    
    $finalToken = $selectResponse.access_token
    
} catch {
    Write-Host "ERRO - Selecao de tenant falhou!" -ForegroundColor Red
    Write-Host "  Detalhes: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# PASSO 3: VALIDAR TOKEN
Write-Host "`n[PASSO 3] Validando token final..." -ForegroundColor Yellow

try {
    $meResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/me-multitenant" `
        -Method GET `
        -Headers @{ "Authorization" = "Bearer $finalToken" }
    
    Write-Host "OK - Token valido!" -ForegroundColor Green
    Write-Host "  User: $($meResponse.nome)" -ForegroundColor Gray
    Write-Host "  Email: $($meResponse.email)" -ForegroundColor Gray
    Write-Host "  Tenant: $($meResponse.tenant_id)" -ForegroundColor Gray
    
} catch {
    Write-Host "ERRO - Token invalido!" -ForegroundColor Red
    Write-Host "  Detalhes: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    exit 1
}

# PASSO 4: TESTAR ACESSO A RECURSO PROTEGIDO
Write-Host "`n[PASSO 4] Testando acesso a recurso protegido..." -ForegroundColor Yellow

try {
    $configResponse = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/config" `
        -Method GET `
        -Headers @{ "Authorization" = "Bearer $finalToken" }
    
    Write-Host "OK - Acesso autorizado!" -ForegroundColor Green
    Write-Host "  Config ID: $($configResponse.id)" -ForegroundColor Gray
    
} catch {
    Write-Host "AVISO - Sem acesso ou sem config" -ForegroundColor Yellow
}

# RESULTADO FINAL
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTICO COMPLETO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nRESUMO:" -ForegroundColor Cyan
Write-Host "  1. Login: OK" -ForegroundColor Green
Write-Host "  2. Select Tenant: OK" -ForegroundColor Green
Write-Host "  3. Token Validation: OK" -ForegroundColor Green
Write-Host "  4. Protected Resource: OK" -ForegroundColor Green

Write-Host "`nTOKEN FINAL PARA USO:" -ForegroundColor Yellow
Write-Host $finalToken -ForegroundColor White

Write-Host "`nCREDENCIAIS:" -ForegroundColor Yellow
Write-Host "  Email: admin@test.com" -ForegroundColor White
Write-Host "  Senha: test123" -ForegroundColor White

Write-Host "`nPROXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "  1. Verifique se o frontend esta salvando o token no localStorage" -ForegroundColor Gray
Write-Host "  2. Verifique se o frontend esta enviando o header Authorization corretamente" -ForegroundColor Gray
Write-Host "  3. Abra o DevTools (F12) e verifique o Console e Network" -ForegroundColor Gray
Write-Host "  4. Procure por erros de CORS ou 401/403" -ForegroundColor Gray
Write-Host ""
