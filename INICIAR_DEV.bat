@echo off
chcp 65001 >nul
title 🔵 LOCAL DEV - Testes e Desenvolvimento

echo.
echo ============================================================================
echo   🔵 AMBIENTE LOCAL DEV (TESTES)
echo ============================================================================
echo.
echo Subindo:
echo   - Banco DEV (porta 5433)
echo   - Backend DEV (porta 8000)
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo Docs:     http://localhost:8000/docs
echo.
echo ⚠️  Use este ambiente apenas para TESTES!
echo ⚠️  Para vendas reais, use INICIAR_PILOTO.bat
echo.
pause

echo.
echo Subindo containers...
docker-compose -f docker-compose.local-dev.yml up -d

echo.
echo ✅ Ambiente DEV iniciado!
echo.
echo Aguardando backend ficar pronto (15 segundos)...
timeout /t 15 /nobreak >nul

echo.
echo ============================================================================
echo   Acesse: http://localhost:5173
echo   Backend: http://localhost:8000/docs
echo ============================================================================
echo.
echo Para ver logs: docker-compose -f docker-compose.local-dev.yml logs -f
echo Para parar: docker-compose -f docker-compose.local-dev.yml down
echo.
pause
