@echo off
setlocal
REM LEGACY_BLOCKED

echo O importador de teste antigo foi bloqueado por seguranca.
echo Ele usava caminho fixo de um computador e nao exigia empresa de destino.
echo.
echo A importacao continua disponivel no codigo, mas precisa da nova camada
echo segura de selecao de empresa e arquivos antes de voltar a ser executada.
exit /b 1
