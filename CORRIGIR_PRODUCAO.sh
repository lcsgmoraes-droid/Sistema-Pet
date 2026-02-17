#!/bin/bash

# =============================================================================
# SCRIPT DE CORREÇÃO AUTOMÁTICA - PRODUÇÃO
# =============================================================================
# Este script corrige problemas comuns no ambiente de produção
# Execute no servidor: bash CORRIGIR_PRODUCAO.sh
# =============================================================================

set -e  # Para na primeira falha

echo "=========================================="
echo "🔧 CORREÇÃO AUTOMÁTICA - PRODUÇÃO"
echo "=========================================="
echo ""

# Diretório do projeto
cd /opt/petshop

echo "✅ Passo 1: Verificando containers..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep petshop

echo ""
echo "✅ Passo 2: Parando containers..."
docker compose -f docker-compose.prod.yml down

echo ""
echo "✅ Passo 3: Corrigindo permissões do frontend..."
chmod -R 755 frontend/dist/ 2>/dev/null || echo "⚠️ Pasta dist não existe (será criada no build)"

echo ""
echo "✅ Passo 4: Limpando migrations conflitantes..."
docker compose -f docker-compose.prod.yml run --rm backend bash -c "
cd /app/alembic/versions
# Remove migrations duplicadas/conflitantes
rm -f *merge*.py
rm -f *20260214_add_racao_ai_fields*.py
echo 'Migrations limpas'
"

echo ""
echo "✅ Passo 5: Verificando estado do banco..."
docker compose -f docker-compose.prod.yml up -d postgres
sleep 5

echo ""
echo "✅ Passo 6: Resetando migrations do banco..."
docker compose -f docker-compose.prod.yml run --rm backend bash -c "
python -c \"
from sqlalchemy import create_engine, text
import os

db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)

with engine.connect() as conn:
    # Remove tabela de controle do alembic
    conn.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))
    conn.commit()
    print('✅ Tabela alembic_version removida')
\"
"

echo ""
echo "✅ Passo 7: Rodando migrations do zero..."
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

echo ""
echo "✅ Passo 8: Subindo todos os containers..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "✅ Passo 9: Aguardando containers ficarem prontos..."
sleep 15

echo ""
echo "✅ Passo 10: Verificando saúde dos containers..."
docker ps --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "✅ Passo 11: Testando API..."
sleep 5
curl -f http://localhost/api/health || echo "⚠️ API ainda não respondeu"

echo ""
echo "=========================================="
echo "✅ CORREÇÃO CONCLUÍDA!"
echo "=========================================="
echo ""
echo "🌐 Acesse: http://mlprohub.com.br"
echo ""
echo "📋 Para ver logs:"
echo "   docker logs petshop-prod-backend --tail 50"
echo "   docker logs petshop-prod-nginx --tail 50"
echo ""
