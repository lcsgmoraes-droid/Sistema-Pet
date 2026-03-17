@echo off
setlocal

if "%~1"=="" (
  powershell -ExecutionPolicy Bypass -File ".\scripts\whatsapp_pilot.ps1" status
  goto :eof
)

powershell -ExecutionPolicy Bypass -File ".\scripts\whatsapp_pilot.ps1" %1
