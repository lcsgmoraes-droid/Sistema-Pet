@echo off
REM ===========================================================================
REM INICIAR DESENVOLVIMENTO - Docker Compose (Backend + Banco)
REM ===========================================================================

echo.
echo ========================================
echo   Pet Shop Pro - DESENVOLVIMENTO
echo ========================================
echo.

REM Verificar se Docker está rodando
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Docker nao esta rodando!
    echo.
    echo Por favor, inicie o Docker Desktop e tente novamente.
    pause
    exit /b 1
)

echo [1/4] Parando outros ambientes...
docker-compose -f docker-compose.production.yml down 2>nul

echo.
echo [2/4] Iniciando containers de DESENVOLVIMENTO...
docker-compose -f docker-compose.development.yml up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao iniciar containers!
    pause
    exit /b 1
)

echo.
echo [3/4] Aguardando containers ficarem prontos (10 segundos)...
timeout /t 10 /nobreak >nul

echo.
echo [4/4] Iniciando Frontend (React + Vite)...
start "Frontend DEV - Pet Shop Pro" cmd /k "cd frontend && npm run dev"

timeout /t 2 >nul

echo.
echo ========================================
echo   DESENVOLVIMENTO - URLs
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Docs API: http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Banco:    PostgreSQL (Docker) localhost:5432
echo Ambiente: DESENVOLVIMENTO
echo.
echo ========================================
echo.
echo Abrindo logs do Backend...
echo (Pressione Ctrl+C para parar de ver os logs)
echo.

REM Mostrar logs do backend em tempo real
docker-compose -f docker-compose.development.yml logs -f backend
