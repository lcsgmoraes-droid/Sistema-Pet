@echo off
echo ════════════════════════════════════════════════════════════════════════════
echo 🧪 EXECUTAR TESTES E2E COMPLETOS - SISTEMA PET SHOP PRO
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo Este script executa TODOS os testes end-to-end do sistema.
echo.
echo 📋 O QUE SERÁ TESTADO:
echo    ✅ Cadastros (Clientes, Pets, Produtos)
echo    ✅ Vendas à vista (Dinheiro, PIX, Débito)
echo    ✅ Vendas parceladas (Cartão Crédito)
echo    ✅ Operações em vendas (Cancelar, Remover item)
echo    ✅ Fluxos complexos (Múltiplos pagamentos, Entrega)
echo    ✅ Validação de TODOS os efeitos colaterais:
echo       - Contas a Receber
echo       - Fluxo de Caixa
echo       - DRE
echo       - Estoque
echo       - Comissões
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo.

REM Vai para a pasta do backend
cd /d "%~dp0backend"

echo 🔍 Verificando se o backend está rodando...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ ERRO: Backend não está rodando!
    echo.
    echo Para iniciar o backend, execute em outro terminal:
    echo    INICIAR_DEV.bat
    echo.
    echo Ou, se preferir produção:
    echo    INICIAR_PRODUCAO.bat
    echo.
    pause
    exit /b 1
)

echo ✅ Backend está rodando!
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo 🚀 INICIANDO TESTES E2E
echo ════════════════════════════════════════════════════════════════════════════
echo.

REM Executa os testes com pytest
pytest tests\e2e_test_sistema_completo.py -v -s --tb=short --color=yes

echo.
echo ════════════════════════════════════════════════════════════════════════════
echo 📊 TESTES FINALIZADOS
echo ════════════════════════════════════════════════════════════════════════════
echo.

if errorlevel 1 (
    echo ❌ ALGUNS TESTES FALHARAM!
    echo    Revise os erros acima e corrija os problemas.
    echo.
) else (
    echo ✅ TODOS OS TESTES PASSARAM!
    echo    Sistema pronto para produção! 🎉
    echo.
)

pause
