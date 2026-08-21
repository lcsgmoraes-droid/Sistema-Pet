@echo off
setlocal
REM COMPATIBILITY_ALIAS
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File ".\scripts\diagnosticar_autenticacao_dev.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
pause
exit /b %EXIT_CODE%
