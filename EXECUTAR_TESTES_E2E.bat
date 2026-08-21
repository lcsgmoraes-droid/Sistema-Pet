@echo off
setlocal
REM COMPATIBILITY_ALIAS
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File ".\scripts\executar_testes_e2e.ps1" %*
exit /b %ERRORLEVEL%
