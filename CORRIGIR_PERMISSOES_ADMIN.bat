@echo off
setlocal
REM COMPATIBILITY_ALIAS
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File ".\scripts\manutencao_banco_dev.ps1" -Operacao corrigir-permissoes-admin
set "EXIT_CODE=%ERRORLEVEL%"
pause
exit /b %EXIT_CODE%
