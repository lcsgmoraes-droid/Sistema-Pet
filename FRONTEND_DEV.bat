@echo off
setlocal
REM COMPATIBILITY_ALIAS
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File ".\scripts\iniciar_frontend_dev.ps1"
exit /b %ERRORLEVEL%
