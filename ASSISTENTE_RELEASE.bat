@echo off
setlocal
REM LEGACY_BLOCKED

echo Este assistente pertence a uma organizacao antiga de commits e foi bloqueado.
echo.
echo Fluxo atual:
echo   1. scripts\git_start_task.ps1
echo   2. trabalhar e validar na branch
echo   3. scripts\git_finish_task.ps1
echo.
echo Consulte CONTRIBUTING.md para o passo a passo oficial.
exit /b 1
