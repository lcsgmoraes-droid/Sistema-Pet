#!/bin/bash

# ==========================================
# EXECUTAR ESTE SCRIPT NO SERVIDOR DE PRODUÇÃO
# ==========================================

set -e

echo "🔄 1. Fazendo pull das mudanças..."
cd /opt/petshop
git pull origin main

echo ""
echo "✅ Arquivos de migração atualizados!"
echo ""

echo "🚀 2. Reiniciando container backend..."
docker restart petshop-prod-backend

echo ""
echo "⏳ Aguardando 5 segundos para o container iniciar..."
sleep 5

echo ""
echo "⬆️  3. Aplicando migrations Alembic..."
docker exec petshop-prod-backend bash -c "cd /app && alembic upgrade head"

echo ""
echo "🔍 4. VALIDANDO tabelas no PostgreSQL..."
docker exec petshop-prod-postgres psql -U petshop_admin -d petshop_prod -c '\dt'

echo ""
echo "✅ 5. Testando importação dos modelos fiscais..."
docker exec petshop-prod-backend python -c "from app.fiscal_models import EmpresaConfigFiscal, FiscalCatalogoProdutos, FiscalEstadoPadrao, KitComposicao, KitConfigFiscal, ProdutoConfigFiscal; print('✅ Todos os modelos fiscais importados com sucesso!')"

echo ""
echo "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
echo ""
echo "Você deve ver todas as tabelas do sistema, incluindo as novas tabelas fiscais."
