@echo off
REM COMPATIBILITY_ALIAS
REM O fluxo local real e unico fica em FLUXO_UNICO.bat.

cd /d "%~dp0"
echo Atalho de compatibilidade: parando o ambiente DEV oficial.
call "%~dp0FLUXO_UNICO.bat" dev-down
exit /b %ERRORLEVEL%
