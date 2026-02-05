# Debug Login
$BASE_URL = "http://localhost:8000"

Write-Host "`n=== DEBUG LOGIN ===" -ForegroundColor Cyan

$body = @{
    email = "admin@test.com"
    password = "admin123"
} | ConvertTo-Json

Write-Host "Body:" -ForegroundColor Yellow
Write-Host $body -ForegroundColor Gray

Write-Host "`nEnviando request..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/auth/login-multitenant" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body `
        -UseBasicParsing
    
    Write-Host "`n[OK] Login com sucesso!" -ForegroundColor Green
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "Content:" -ForegroundColor Yellow
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "`n[ERRO] Login falhou!" -ForegroundColor Red
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    
    if ($_.ErrorDetails) {
        Write-Host "Detalhes:" -ForegroundColor Red
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
    
    # Tentar ler response body
    try {
        $result = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($result)
        $reader.BaseStream.Position = 0
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body:" -ForegroundColor Red
        Write-Host $responseBody -ForegroundColor Red
    } catch {}
}

Write-Host ""
