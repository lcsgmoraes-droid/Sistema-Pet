@echo off
REM COMPATIBILITY_ALIAS
REM O backend local oficial roda no ambiente DEV padronizado.

cd /d "%~dp0"
echo Atalho de compatibilidade: iniciando o ambiente DEV oficial.
call "%~dp0FLUXO_UNICO.bat" dev-up
exit /b %ERRORLEVEL%
