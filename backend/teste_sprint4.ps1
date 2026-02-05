# Teste Sprint 4 - Sentiment Analysis & Handoff

$loginBody = @{email="admin@test.com"; password="test123"} | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login-multitenant" -Method POST -Headers @{"Content-Type"="application/json"} -Body $loginBody
$tenant_id = $loginResponse.tenants[0].id
$token = $loginResponse.access_token
$selectBody = @{tenant_id=$tenant_id} | ConvertTo-Json
$selectResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/select-tenant" -Method POST -Headers @{"Content-Type"="application/json"; "Authorization"="Bearer $token"} -Body $selectBody
$finalToken = $selectResponse.access_token

Write-Host "`n=== TESTE 1: Mensagem Normal ===" -ForegroundColor Cyan
$msg1 = @{message="Oi, tudo bem?"; phone_number="+5511999999999"} | ConvertTo-Json
try {
    $r1 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg1 -TimeoutSec 30
    Write-Host "✅ Intent: $($r1.intent)" -ForegroundColor Green
    Write-Host "Handoff: $($r1.requires_human)" -ForegroundColor Gray
    Write-Host $r1.response -ForegroundColor White
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

Start-Sleep -Seconds 2

Write-Host "`n=== TESTE 2: Solicitar Atendente ===" -ForegroundColor Cyan
$msg2 = @{message="Quero falar com um atendente"; phone_number="+5511999999999"} | ConvertTo-Json
try {
    $r2 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg2 -TimeoutSec 30
    Write-Host "✅ Intent: $($r2.intent)" -ForegroundColor Green
    Write-Host "Handoff: $($r2.requires_human)" -ForegroundColor Yellow
    if ($r2.handoff_id) {
        Write-Host "Handoff ID: $($r2.handoff_id)" -ForegroundColor Cyan
    }
    Write-Host $r2.response -ForegroundColor White
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

Start-Sleep -Seconds 2

Write-Host "`n=== TESTE 3: Mensagem Irritada ===" -ForegroundColor Cyan
$msg3 = @{message="Isso é um absurdo! Péssimo atendimento, estou muito irritado!"; phone_number="+5511888888888"} | ConvertTo-Json
try {
    $r3 = Invoke-RestMethod -Uri "http://localhost:8000/api/whatsapp/test/message" -Method POST -Headers @{"Authorization"="Bearer $finalToken"; "Content-Type"="application/json"} -Body $msg3 -TimeoutSec 30
    Write-Host "✅ Intent: $($r3.intent)" -ForegroundColor Green
    Write-Host "Handoff: $($r3.requires_human)" -ForegroundColor Red
    if ($r3.handoff_id) {
        Write-Host "Handoff ID: $($r3.handoff_id)" -ForegroundColor Cyan
        if ($r3.sentiment) {
            Write-Host "Sentiment: $($r3.sentiment.label) ($($r3.sentiment.score))" -ForegroundColor Gray
        }
    }
    Write-Host $r3.response -ForegroundColor White
} catch {
    Write-Host "❌ Erro: $_" -ForegroundColor Red
}

Write-Host "`n=== RESUMO ===" -ForegroundColor Cyan
Write-Host "Sprint 4 - Sentiment Analysis & Handoff testado!" -ForegroundColor Green
