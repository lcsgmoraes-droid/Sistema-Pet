@echo off
REM ===============================================
REM Script de Teste - Diagnóstico de Autenticação
REM ===============================================

echo.
echo ========================================
echo  Diagnóstico Sistema Pet - Conciliacao
echo ========================================
echo.

REM Verificar se o backend está rodando
echo [1/4] Verificando backend...
docker ps --filter "name=petshop-dev-backend" --format "table {{.Names}}\t{{.Status}}" > nul 2>&1
if errorlevel 1 (
    echo ❌ Backend NAO esta rodando!
    echo Execute: docker compose -f docker-compose.development.yml up -d
    pause
    exit /b 1
) else (
    echo ✅ Backend esta rodando
)

echo.
echo [2/4] Testando endpoint de operadoras (sem auth - deve retornar 401)...
curl -s http://127.0.0.1:8000/api/operadoras-cartao?apenas_ativas=true
echo.

echo.
echo [3/4] Verificando saude do backend...
curl -s http://127.0.0.1:8000/health
echo.

echo.
echo [4/4] Instrucoes para testar no browser:
echo.
echo  1. Abra o DevTools (F12) no navegador
echo  2. Va para a aba Console
echo  3. Execute os comandos do arquivo DIAGNOSTICO_AUTENTICACAO.md
echo.
echo ========================================
echo  Teste Concluido
echo ========================================
echo.
echo Proximos passos:
echo  1. Acesse: http://localhost:5173/login
echo  2. Faca login com suas credenciais
echo  3. Navegue para: http://localhost:5173/financeiro/conciliacao-3abas
echo  4. Observe os logs no Console do navegador
echo.
pause
