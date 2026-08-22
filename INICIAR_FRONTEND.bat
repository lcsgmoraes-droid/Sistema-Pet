@echo off
REM COMPATIBILITY_ALIAS
REM A implementacao oficial fica em scripts\iniciar_frontend_dev.ps1.

cd /d "%~dp0"
echo Atalho de compatibilidade: iniciando o frontend DEV oficial.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_frontend_dev.ps1"
exit /b %ERRORLEVEL%
