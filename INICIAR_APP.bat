@echo off
REM COMPATIBILITY_ALIAS
REM A implementacao oficial fica em scripts\iniciar_app_mobile.ps1.

cd /d "%~dp0"
echo Atalho de compatibilidade: iniciando o app pelo fluxo local oficial.

if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_app_mobile.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_app_mobile.ps1" -ApiUrl "%~1"
)

exit /b %ERRORLEVEL%
