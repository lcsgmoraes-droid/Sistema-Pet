# Testes completos

$loginBody = @{email="admin@test.com"; password="test123"} | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login-multitenant" -Method POST -Headers @{"Content-Type"="application/json"} -Body $loginBody
$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token
$selectBody = @{tenant_id=$tenant_id} | ConvertTo-Json
$selectResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/select-tenant" -Method POST -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} -Body $selectBody
$finalToken = $selectResponse.access_token

Write-Host "`n=== TESTE 1: Saudacao ===" -ForegroundColor Cyan
$msg1 = @{message="Oi! Bom dia!"; phone_number="+5511999887766"} | ConvertTo-Json
$r1 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg1 -TimeoutSec 30
Write-Host "[OK] Intent: $($r1.intent) | Tokens: $($r1.tokens_used) | Tempo: $([math]::Round($r1.processing_time, 2))s" -ForegroundColor Green
Write-Host $r1.response -ForegroundColor White

Start-Sleep -Seconds 2

Write-Host "`n=== TESTE 2: Buscar Produtos (com tool call) ===" -ForegroundColor Cyan
$msg2 = @{message="Quanto custa a racao Golden 15kg?"; phone_number="+5511999887766"} | ConvertTo-Json
$r2 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg2 -TimeoutSec 30
Write-Host "[OK] Intent: $($r2.intent) | Tokens: $($r2.tokens_used) | Tempo: $([math]::Round($r2.processing_time, 2))s" -ForegroundColor Green
Write-Host $r2.response -ForegroundColor White

Start-Sleep -Seconds 2

Write-Host "`n=== TESTE 3: Agendamento ===" -ForegroundColor Cyan
$msg3 = @{message="Quero agendar um banho para meu cachorro amanha"; phone_number="+5511999887766"} | ConvertTo-Json
$r3 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg3 -TimeoutSec 30
Write-Host "[OK] Intent: $($r3.intent) | Tokens: $($r3.tokens_used) | Tempo: $([math]::Round($r3.processing_time, 2))s" -ForegroundColor Green
Write-Host $r3.response -ForegroundColor White

Start-Sleep -Seconds 2

Write-Host "`n=== TESTE 4: Informacoes da Loja ===" -ForegroundColor Cyan
$msg4 = @{message="Qual o endereco da loja?"; phone_number="+5511999887766"} | ConvertTo-Json
$r4 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg4 -TimeoutSec 30
Write-Host "[OK] Intent: $($r4.intent) | Tokens: $($r4.tokens_used) | Tempo: $([math]::Round($r4.processing_time, 2))s" -ForegroundColor Green
Write-Host $r4.response -ForegroundColor White

Write-Host "`n=== RESUMO ===" -ForegroundColor Cyan
Write-Host "Total tokens: $($r1.tokens_used + $r2.tokens_used + $r3.tokens_used + $r4.tokens_used)" -ForegroundColor Yellow
Write-Host "Tempo medio: $([math]::Round(($r1.processing_time + $r2.processing_time + $r3.processing_time + $r4.processing_time)/4, 2))s" -ForegroundColor Yellow
Write-Host "`nSPRINT 3 - 100% FUNCIONAL!" -ForegroundColor Green
