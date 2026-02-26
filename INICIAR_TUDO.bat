@echo off
chcp 65001 >nul
title INICIAR DEV

echo.
echo ============================================================================
echo   INICIAR AMBIENTE DEV
echo ============================================================================
echo.
echo Subindo:
echo   DEV - Backend porta 8000, Banco porta 5433
echo.
pause

echo.
echo Subindo DEV...
docker-compose -f docker-compose.local-dev.yml up -d

echo.
echo Aguardando backend ficar pronto (20 segundos)...
timeout /t 20 /nobreak >nul

echo.
echo ============================================================================
echo   DEV: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo ============================================================================
echo.
echo Para ver logs: docker-compose -f docker-compose.local-dev.yml logs -f
echo Para parar: PARAR_TUDO.bat
echo.
pause
