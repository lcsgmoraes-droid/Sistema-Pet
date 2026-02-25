@echo off
cd /d "%~dp0"

set ACAO=%1
if "%ACAO%"=="" set ACAO=status

powershell -ExecutionPolicy Bypass -File ".\scripts\fluxo_unico.ps1" %ACAO%
pause
