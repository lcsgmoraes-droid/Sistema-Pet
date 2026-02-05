@echo off
REM ===========================================================================
REM Script de Backup Automático para OneDrive/Google Drive
REM ===========================================================================
REM Execute este script diariamente para garantir backup em nuvem
REM Pode ser agendado no "Agendador de Tarefas" do Windows
REM ===========================================================================

echo ========================================
echo   Backup Automatico para Nuvem
echo ========================================
echo.

SET BACKUP_DIR=%~dp0..\backups
SET CLOUD_DIR=%USERPROFILE%\OneDrive\Backups_PetShop

REM Criar diretório na nuvem se não existir
if not exist "%CLOUD_DIR%" (
    echo Criando diretorio na nuvem: %CLOUD_DIR%
    mkdir "%CLOUD_DIR%"
)

REM Verificar se há backups para copiar
if not exist "%BACKUP_DIR%\backup_*.dump.gz" (
    echo [ERRO] Nenhum backup encontrado em %BACKUP_DIR%
    echo Certifique-se que o servico de backup esta rodando!
    pause
    exit /b 1
)

REM Copiar últimos 7 dias de backups
echo Copiando backups recentes para OneDrive...
echo Origem: %BACKUP_DIR%
echo Destino: %CLOUD_DIR%
echo.

robocopy "%BACKUP_DIR%" "%CLOUD_DIR%" backup_*.dump.gz /maxage:7 /MT:8 /R:3 /W:5

if %ERRORLEVEL% LEQ 3 (
    echo.
    echo ========================================
    echo   [OK] Backup para nuvem concluido!
    echo ========================================
    echo.
    
    REM Mostrar últimos backups copiados
    echo Ultimos backups na nuvem:
    dir /O-D /B "%CLOUD_DIR%\backup_*.dump.gz" 2>nul | findstr /R "backup_.*\.dump\.gz" | more +0
    echo.
) else (
    echo.
    echo [ERRO] Falha ao copiar backups. Codigo de erro: %ERRORLEVEL%
    pause
    exit /b 1
)

REM Opcional: Limpar backups muito antigos da nuvem (>90 dias)
echo Limpando backups antigos (mais de 90 dias)...
forfiles /P "%CLOUD_DIR%" /M backup_*.dump.gz /D -90 /C "cmd /c del @path" 2>nul

echo.
echo Concluido! Pressione qualquer tecla para fechar.
pause >nul
