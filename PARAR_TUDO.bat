@echo off
chcp 65001 >nul
title PARAR DEV

echo.
echo ============================================================================
echo   PARAR AMBIENTE DEV
echo ============================================================================
echo.
pause

echo.
echo Parando DEV...
docker-compose -f docker-compose.local-dev.yml down

echo.
echo Ambiente DEV parado!
echo.
echo Para iniciar novamente: INICIAR_DEV.bat
echo.
pause
