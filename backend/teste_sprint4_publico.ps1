# Teste direto Sprint 4 - Sem autenticacao primeiro
$ErrorActionPreference = "Stop"
$BASE_URL = "http://localhost:8000"

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  TESTE SPRINT 4 - ENDPOINTS PUBLICOS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 1. Verificar OpenAPI
Write-Host "`n[1] Verificando OpenAPI..." -ForegroundColor Yellow
$api = Invoke-RestMethod -Uri "$BASE_URL/openapi.json"
$endpoints = @()
$api.paths.Keys | Where-Object { $_ -like "*whatsapp*" } | ForEach-Object {
    $path = $_
    $api.paths.$path.Keys | ForEach-Object {
        $endpoints += "$_ $path"
    }
}
Write-Host "    OK - Total de endpoints WhatsApp: $($endpoints.Count)" -ForegroundColor Green
$endpoints | Select-Object -First 10 | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }

# 2. Tentar um endpoint simples (deve dar 401 se estiver protegido)
Write-Host "`n[2] Testando endpoint de agents (esperado 401)..." -ForegroundColor Yellow
try {
    $agents = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/agents" -Method GET
    Write-Host "    AVISO - Endpoint desprotegido!" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "    OK - Endpoint protegido (401 Unauthorized)" -ForegroundColor Green
    } else {
        Write-Host "    ERRO - Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

# 3. Testar sentiment (também deve dar 401)
Write-Host "`n[3] Testando endpoint de sentiment (esperado 401)..." -ForegroundColor Yellow
try {
    $body = @{ message = "teste" } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "$BASE_URL/api/whatsapp/test-sentiment" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body
    Write-Host "    AVISO - Endpoint desprotegido!" -ForegroundColor Yellow
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "    OK - Endpoint protegido (401 Unauthorized)" -ForegroundColor Green
    } else {
        Write-Host "    ERRO - Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  ENDPOINTS SPRINT 4 REGISTRADOS!" -ForegroundColor Green  
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "`nProximo passo: Resolver problema de login" -ForegroundColor Yellow
Write-Host "Depois executar teste completo com autenticacao" -ForegroundColor Gray
