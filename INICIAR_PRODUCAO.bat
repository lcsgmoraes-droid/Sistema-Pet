@echo off
REM ===========================================================================
REM INICIAR PRODUÇÃO - Ambiente Docker (Dados Reais)
REM ===========================================================================

echo.
echo ========================================
echo   Pet Shop Pro - PRODUCAO
echo   DADOS REAIS - CUIDADO!
echo ========================================
echo.

REM Verificar se .env.production existe
if not exist ".env.production" (
    echo [ERRO] Arquivo .env.production nao encontrado!
    echo.
    echo Por favor, crie o arquivo .env.production com as configuracoes de producao.
    pause
    exit /b 1
)

REM Verificar se Docker está rodando
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Docker nao esta rodando!
    echo.
    echo Por favor, inicie o Docker Desktop e tente novamente.
    pause
    exit /b 1
)

echo [1/5] Parando outros ambientes...
docker-compose -f docker-compose.yml down 2>nul
docker-compose -f docker-compose.staging.yml down 2>nul
docker-compose -f docker-compose.local-prod.yml down 2>nul

echo.
echo [2/5] Criando diretorio de backups...
if not exist "backups" mkdir backups

echo.
echo [3/5] Iniciando containers de PRODUCAO...
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao iniciar containers!
    echo Verifique o arquivo .env.production
    pause
    exit /b 1
)

echo.
echo [4/5] Aguardando containers ficarem prontos (30 segundos)...
timeout /t 30 /nobreak >nul

echo.
echo [5/5] Verificando saude do sistema...
echo.

curl -s http://localhost:8000/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend esta respondendo!
) else (
    echo [AVISO] Backend ainda nao esta pronto.
    echo Aguarde mais alguns segundos e acesse: http://localhost:8000/docs
)

echo.
echo ========================================
echo   PRODUCAO - URLs
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Docs API: http://localhost:8000/docs
echo Frontend: Execute 'cd frontend && npm run dev'
echo.
echo Banco:    PostgreSQL (Docker)
echo Porta:    5432
echo Backups:  ./backups/ (automatico a cada 6h)
echo Ambiente: PRODUCAO
echo.
echo ========================================
echo.
echo Status dos containers:
docker-compose -f docker-compose.production.yml --env-file .env.production ps
echo.
echo Para parar: docker-compose -f docker-compose.production.yml down
echo Para logs:  docker-compose -f docker-compose.production.yml logs -f
echo.
pause
