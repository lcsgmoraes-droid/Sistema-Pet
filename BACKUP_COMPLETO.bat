@echo off
REM ===========================================================================
REM BACKUP COMPLETO DO SISTEMA
REM ===========================================================================
REM Salva TUDO: banco, código, configs, uploads, documentação
REM ===========================================================================

echo ========================================
echo   Backup Completo do Sistema
echo ========================================
echo.
echo Este script vai criar um backup de:
echo   - Bancos de dados (staging + prod local)
echo   - Codigo fonte completo
echo   - Configuracoes (.env)
echo   - Uploads
echo   - Backups anteriores
echo   - Documentacao
echo.
echo O backup sera salvo em: backups\backup_completo_YYYYMMDD_HHMMSS.zip
echo.
pause
echo.

REM Verificar Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao encontrado!
    pause
    exit /b 1
)

REM Verificar Docker
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] Docker nao esta rodando.
    echo O backup sera feito apenas do codigo e configs.
    echo.
    pause
)

echo Executando backup completo...
echo.

python scripts\backup_completo.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   BACKUP CONCLUIDO!
    echo ========================================
    echo.
    echo IMPORTANTE:
    echo 1. Copie o arquivo .zip para local seguro
    echo 2. OneDrive, Google Drive ou HD externo
    echo 3. Mantenha multiplas copias
    echo.
) else (
    echo.
    echo [ERRO] Falha ao criar backup!
    echo.
)

pause
