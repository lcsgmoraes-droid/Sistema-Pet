# Verificar endpoints da Sprint 4
$ErrorActionPreference = "Continue"

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "  VERIFICANDO ENDPOINTS SPRINT 4" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

try {
    $api = Invoke-RestMethod -Uri "http://127.0.0.1:8000/openapi.json" -Method GET
    
    Write-Host "`nTotal de endpoints: $($api.paths.Count)" -ForegroundColor Gray
    
    Write-Host "`nEndpoints Sprint 4 (WhatsApp Handoff):" -ForegroundColor Yellow
    $handoffEndpoints = $api.paths.Keys | Where-Object { $_ -like "*whatsapp*agent*" -or $_ -like "*whatsapp*handoff*" }
    
    if ($handoffEndpoints.Count -gt 0) {
        foreach ($endpoint in $handoffEndpoints) {
            $methods = $api.paths.$endpoint.Keys -join ", "
            Write-Host "  ✓ $endpoint [$methods]" -ForegroundColor Green
        }
        Write-Host "`n[OK] Endpoints Sprint 4 registrados!" -ForegroundColor Green
    } else {
        Write-Host "  [ERRO] Nenhum endpoint encontrado!" -ForegroundColor Red
    }
    
    # Verificar tags
    Write-Host "`nTags disponiveis:" -ForegroundColor Yellow
    $tags = $api.tags | Where-Object { $_.name -like "*WhatsApp*" }
    foreach ($tag in $tags) {
        Write-Host "  - $($tag.name)" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "[ERRO] $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
