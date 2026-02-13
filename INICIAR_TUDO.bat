@echo off
chcp 65001 >nul
title 🔄 INICIAR TUDO - DEV + PILOTO

echo.
echo ============================================================================
echo   🔄 INICIAR AMBOS AMBIENTES
echo ============================================================================
echo.
echo Subindo:
echo   🔵 DEV    - Backend porta 8000, Banco porta 5433
echo   🟢 PILOTO - Backend porta 8001, Banco porta 5434
echo.
echo ⚠️  Os 2 ambientes vão rodar SIMULTANEAMENTE
echo.
pause

echo.
echo [1/2] Subindo DEV...
docker-compose -f docker-compose.local-dev.yml up -d

echo.
echo [2/2] Subindo PILOTO...
docker-compose -f docker-compose.local-piloto.yml up -d

echo.
echo ✅ Ambos ambientes iniciados!
echo.
echo Aguardando backends ficarem prontos (25 segundos)...
timeout /t 25 /nobreak >nul

echo.
echo ============================================================================
echo   🔵 DEV:    http://localhost:8000/docs
echo   🟢 PILOTO: http://localhost:8001/docs
echo   Frontend:  http://localhost:5173
echo ============================================================================
echo.
echo Para ver logs:
echo   DEV:    docker-compose -f docker-compose.local-dev.yml logs -f
echo   PILOTO: docker-compose -f docker-compose.local-piloto.yml logs -f
echo.
echo Para parar tudo: PARAR_TUDO.bat
echo.
pause
