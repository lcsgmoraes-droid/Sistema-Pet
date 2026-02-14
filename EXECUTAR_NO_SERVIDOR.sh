#!/bin/bash

# ==========================================
# EXECUTAR ESTE SCRIPT NO SERVIDOR DE PRODUÇÃO
# ==========================================

set -e

echo "🔄 1. Fazendo pull das mudanças..."
cd /opt/petshop
git pull origin main

echo ""
echo "✅ Arquivos atualizados!"
echo ""

echo "📂 2. Verificando estrutura db/..."
ls -la /opt/petshop/backend/app/db/

echo ""
echo "🔨 3. Rebuild do container backend (--no-cache)..."
docker compose --env-file .env.production -f docker-compose.prod.yml build --no-cache backend

echo ""
echo "🚀 4. Reiniciando container backend..."
docker compose --env-file .env.production -f docker-compose.prod.yml up -d backend

echo ""
echo "⏳ Aguardando 10 segundos para o container iniciar..."
sleep 10

echo ""
echo "🔍 5. VALIDANDO estrutura dentro do container..."
docker exec petshop-prod-backend bash -c "ls -la /app/app/db/"

echo ""
echo "📄 6. Verificando conteúdo de base_class.py..."
docker exec petshop-prod-backend bash -c "head -15 /app/app/db/base_class.py"

echo ""
echo "✅ ESTRUTURA DB CRIADA COM SUCESSO!"
echo ""

echo "🗃️  7. Executando migrations Alembic..."
docker exec petshop-prod-backend bash -c "cd /app && alembic revision --autogenerate -m 'initial_schema'"

echo ""
echo "⬆️  8. Aplicando migrations..."
docker exec petshop-prod-backend bash -c "cd /app && alembic upgrade head"

echo ""
echo "🔍 9. VALIDANDO tabelas no PostgreSQL..."
docker exec petshop-prod-postgres psql -U petshop_admin -d petshop_prod -c '\dt'

echo ""
echo "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
echo ""
echo "Você deve ver as seguintes tabelas:"
echo "  ✓ alembic_version"
echo "  ✓ empresa_config_fiscal"
echo "  ✓ fiscal_catalogo_produtos"
echo "  ✓ fiscal_estado_padrao"
echo "  ✓ kit_composicao"
echo "  ✓ kit_config_fiscal"
echo "  ✓ produto_config_fiscal"
