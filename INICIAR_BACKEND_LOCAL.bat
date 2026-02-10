@echo off
REM ===========================================================================
REM INICIAR BACKEND LOCAL (Sem Docker) - Modo Desenvolvimento
REM ===========================================================================

echo.
echo ========================================
echo   Pet Shop Pro - BACKEND LOCAL
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Ativando ambiente virtual...
call .venv\Scripts\activate.bat

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ambiente virtual nao encontrado!
    echo Execute: python -m venv .venv
    pause
    exit /b 1
)

echo.
echo [2/3] Configurando variaveis de ambiente...
if exist .env.development (
    echo Usando .env.development
    copy /Y .env.development .env >nul
) else if exist .env (
    echo Usando .env existente
) else (
    echo [AVISO] Arquivo .env nao encontrado - usando configuracoes padrao
)

echo.
echo [3/3] Iniciando servidor FastAPI (uvicorn)...
echo.
echo ========================================
echo   BACKEND RODANDO
echo ========================================
echo   URL: http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo   Redoc: http://localhost:8000/redoc
echo ========================================
echo.

cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
