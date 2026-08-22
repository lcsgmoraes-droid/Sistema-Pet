@echo off
setlocal
REM LEGACY_BLOCKED

echo O antigo frontend piloto local foi descontinuado e esta bloqueado.
echo Ele dependia de uma configuracao removida e podia misturar DEV com dados reais.
echo.
echo Para desenvolvimento, use: INICIAR_FRONTEND.bat
echo Para empresas reais, acesse somente o dominio oficial publicado.
exit /b 1
