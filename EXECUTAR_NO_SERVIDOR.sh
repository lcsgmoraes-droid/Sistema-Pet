#!/bin/bash

# ==========================================
# DEPLOY COMPLETO - SERVIDOR DE PRODUÇÃO
# ==========================================

set -e

echo "🔄 1. Fazendo pull das mudanças..."
cd /opt/petshop
git pull origin main

echo ""
echo "✅ Código atualizado!"
echo ""

echo "🔍 2. Verificando arquivo .env.production..."
if [ ! -f .env.production ]; then
    echo "❌ ERRO: Arquivo .env.production não encontrado!"
    echo "📝 Copie o arquivo .env.production do seu ambiente local para o servidor."
    exit 1
fi

# Verificar se as variáveis essenciais estão definidas
if ! grep -q "^POSTGRES_PASSWORD=" .env.production || ! grep -q "^JWT_SECRET_KEY=" .env.production; then
    echo "❌ ERRO: Variáveis POSTGRES_PASSWORD ou JWT_SECRET_KEY não definidas!"
    echo "📝 Verifique o arquivo .env.production"
    exit 1
fi

echo "✅ Arquivo .env.production OK!"
echo ""

echo "🛑 3. Parando containers antigos..."
docker compose -f docker-compose.prod.yml down || true

echo ""
echo "🏗️  4. Fazendo build e iniciando containers..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

echo ""
echo "⏳ 5. Aguardando containers iniciarem..."
sleep 10

echo ""
echo "🔍 6. Verificando status dos containers..."
docker compose -f docker-compose.prod.yml ps

echo ""
echo "⬆️  7. Aplicando migrations Alembic..."
docker exec petshop-prod-backend bash -c "cd /app && alembic upgrade head"

echo ""
echo "🔍 8. Validando variáveis de ambiente..."
echo "SQL_AUDIT_ENFORCE_LEVEL:"
docker exec petshop-prod-backend env | grep SQL_AUDIT || echo "⚠️  Variável não encontrada"

echo ""
echo "🔍 9. Verificando tabelas no PostgreSQL..."
docker exec petshop-prod-postgres psql -U petshop_admin -d petshop_prod -c '\dt' || echo "⚠️  Não foi possível conectar ao banco"

echo ""
echo "✅ 10. Testando health check do backend..."
sleep 5
curl -f http://localhost:8000/health || echo "⚠️  Health check falhou - verifique os logs"

echo ""
echo "📊 Logs recentes do backend:"
docker logs --tail=20 petshop-prod-backend

echo ""
echo "🎉 DEPLOY CONCLUÍDO!"
echo ""
echo "✅ Para verificar se está tudo OK:"
echo "   docker compose -f docker-compose.prod.yml ps"
echo "   docker logs petshop-prod-backend"
echo "   docker logs petshop-prod-frontend"
