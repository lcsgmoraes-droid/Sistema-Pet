# Teste simplificado

$loginBody = @{email="admin@test.com"; password="test123"} | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login-multitenant" -Method POST -Headers @{"Content-Type"="application/json"} -Body $loginBody

$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token

$selectBody = @{tenant_id=$tenant_id} | ConvertTo-Json
$selectResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/select-tenant" -Method POST -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} -Body $selectBody

$finalToken = $selectResponse.access_token

Write-Host "`n1. Verificando config..." -ForegroundColor Cyan

try {
    $config = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/config" -Method GET -Headers @{"Authorization"="Bearer $finalToken"}
    Write-Host "[OK] Config encontrada!" -ForegroundColor Green
    Write-Host "Bot: $($config.bot_name)" -ForegroundColor Gray
    Write-Host "Tone: $($config.tone)" -ForegroundColor Gray
    Write-Host "Model: $($config.model_preference)" -ForegroundColor Gray
    Write-Host "Auto: $($config.auto_response_enabled)" -ForegroundColor Gray
    Write-Host "OpenAI Key: $($config.openai_api_key.Substring(0, 20))..." -ForegroundColor Gray
} catch {
    Write-Host "[ERRO] $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Testando intent..." -ForegroundColor Cyan

try {
    $intentBody = @{message="Oi!"} | ConvertTo-Json
    $intentResult = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/intent" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $intentBody
    Write-Host "[OK] Intent: $($intentResult.intent) ($($intentResult.confidence))" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n3. Testando mensagem com IA..." -ForegroundColor Cyan
Start-Sleep -Seconds 1

try {
    $msgBody = @{message="Oi!"; phone_number="+5511999887766"} | ConvertTo-Json
    $msgResult = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msgBody -TimeoutSec 30
    
    Write-Host "[OK] IA RESPONDEU!" -ForegroundColor Green
    Write-Host "Intent: $($msgResult.intent) ($($msgResult.confidence))" -ForegroundColor Gray
    Write-Host "Tokens: $($msgResult.tokens_used)" -ForegroundColor Gray
    Write-Host "Tempo: $([math]::Round($msgResult.processing_time, 2))s" -ForegroundColor Gray
    Write-Host "`nResposta:" -ForegroundColor Cyan
    Write-Host $msgResult.response -ForegroundColor White
    
} catch {
    Write-Host "[ERRO] Falha no teste" -ForegroundColor Red
    Write-Host "Message: $($_.Exception.Message)" -ForegroundColor Yellow
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Gray
    }
}
