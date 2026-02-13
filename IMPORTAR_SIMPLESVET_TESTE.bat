@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════════════════
echo      🔄 IMPORTADOR SIMPLESVET - TESTE (20 REGISTROS)
echo ═══════════════════════════════════════════════════════════
echo.
echo Importando dados do SimplesVet para o Sistema Pet...
echo Apenas 20 registros para validação inicial
echo.
echo ⚠️  CERTIFIQUE-SE:
echo    1. Banco de dados DEV está rodando
echo    2. Arquivos CSV estão em C:\Users\Lucas\Downloads\simplesvet\banco
echo.
pause
echo.
echo 🚀 Iniciando importação...
echo.

cd /d "%~dp0backend"

python importar_simplesvet.py --all --limite 20

echo.
echo ═══════════════════════════════════════════════════════════
echo ✅ Importação concluída!
echo ═══════════════════════════════════════════════════════════
echo.
echo Próximos passos:
echo 1. Acessar o sistema: http://localhost:3000
echo 2. Verificar clientes, produtos, pets e vendas
echo 3. Validar se os relacionamentos estão corretos
echo.
pause
