@echo off
setlocal
REM COMPATIBILITY_ALIAS
cd /d "%~dp0"

if "%~1"=="" (
  powershell -ExecutionPolicy Bypass -File ".\scripts\whatsapp_pilot.ps1" status
  exit /b %ERRORLEVEL%
)

powershell -ExecutionPolicy Bypass -File ".\scripts\whatsapp_pilot.ps1" %1
exit /b %ERRORLEVEL%
