@echo off
setlocal
REM COMPATIBILITY_ALIAS
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\importar_simplesvet_seguro.ps1" %*
exit /b %errorlevel%
