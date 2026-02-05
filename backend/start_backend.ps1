# Iniciar Backend
cd "c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend"
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  BACKEND - SPRINT 4 RUNNING" -ForegroundColor Green
Write-Host "  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Green

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Write-Host "`nBackend encerrado. Pressione qualquer tecla para fechar..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
