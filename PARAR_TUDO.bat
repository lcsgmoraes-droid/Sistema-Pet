@echo off
chcp 65001 >nul
title 🛑 PARAR TUDO

echo.
echo ============================================================================
echo   🛑 PARAR TODOS OS AMBIENTES
echo ============================================================================
echo.
echo Parando:
echo   🔵 DEV
echo   🟢 PILOTO
echo.
pause

echo.
echo [1/2] Parando DEV...
docker-compose -f docker-compose.local-dev.yml down

echo.
echo [2/2] Parando PILOTO...
docker-compose -f docker-compose.local-piloto.yml down

echo.
echo ✅ Todos os ambientes foram parados!
echo.
echo Para iniciar novamente:
echo   DEV:    INICIAR_DEV.bat
echo   PILOTO: INICIAR_PILOTO.bat
echo   AMBOS:  INICIAR_TUDO.bat
echo.
pause
