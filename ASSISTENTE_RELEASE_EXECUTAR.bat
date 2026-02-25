@echo off
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -File ".\scripts\assistente_release_seguro.ps1" -ExecutarCommit -ExecutarPush
pause
