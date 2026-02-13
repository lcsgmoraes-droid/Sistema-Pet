@echo off
chcp 65001 >nul
title 🟢 CRIAR BANCO DE PRODUÇÃO - Pet Shop Pro

echo.
echo ============================================================================
echo   🟢 CRIAR BANCO DE PRODUÇÃO LIMPO (PILOTO)
echo ============================================================================
echo.
echo Este script vai:
echo   1. Subir o banco de produção (porta 5433)
echo   2. Aplicar migrations (estrutura completa)
echo   3. Copiar configurações essenciais
echo   4. Criar usuário admin
echo   5. Deixar produtos/vendas/clientes VAZIOS
echo.
echo ⚠️  ATENÇÃO: Só execute isso UMA VEZ para criar o banco!
echo.
pause

echo.
echo [1/3] Subindo banco de produção...
docker-compose -f docker-compose.production-local.yml up -d postgres-prod

echo.
echo [2/3] Aguardando banco inicializar (30 segundos)...
timeout /t 30 /nobreak >nul

echo.
echo [3/3] Criando banco limpo com configurações...
python backend\criar_banco_producao.py

echo.
echo ============================================================================
echo   ✅ CONCLUÍDO!
echo ============================================================================
echo.
echo Próximo passo: Subir o backend de produção
echo   docker-compose -f docker-compose.production-local.yml up -d backend-prod
echo.
echo Ou use: INICIAR_PRODUCAO_LOCAL.bat
echo.
pause
