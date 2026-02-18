# Script para executar importação completa do SimplesVet
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  IMPORTAÇÃO COMPLETA DO SIMPLESVET" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Set-Location "c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend"

Write-Host "Iniciando importação de TODOS os produtos..." -ForegroundColor Yellow
Write-Host ""

# Executar importação
python importar_simplesvet.py --fase 2

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  IMPORTAÇÃO CONCLUÍDA" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verifique os logs em: logs_importacao/" -ForegroundColor Yellow

# Exibir último arquivo CSV gerado
$ultimoCsv = Get-ChildItem "logs_importacao\produtos_nao_importados_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($ultimoCsv) {
    Write-Host ""
    Write-Host "Último relatório de não importados:" -ForegroundColor Cyan
    Write-Host $ultimoCsv.FullName -ForegroundColor White
    Write-Host ""
    Write-Host "Primeiras 10 linhas:" -ForegroundColor Cyan
    Get-Content $ultimoCsv.FullName -Head 10
}
