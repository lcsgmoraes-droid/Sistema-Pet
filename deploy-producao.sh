#!/bin/bash
# ==============================================
# SCRIPT DE DEPLOY PRODUÇÃO - MLPROHUB
# ==============================================

set -e  # Parar em caso de erro

echo "🚀 INICIANDO DEPLOY PRODUÇÃO"
echo "=============================="
echo ""

# Verificar se está no diretório correto
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Erro: docker-compose.prod.yml não encontrado"
    echo "Execute este script de /opt/petshop"
    exit 1
fi

echo "📂 Diretório: $(pwd)"
echo ""

# PASSO 1: Limpar modificações locais e atualizar
echo "📥 PASSO 1: Atualizando código do Git..."
git fetch origin
echo "   - Descartando modificações locais (se houver)"
git reset --hard origin/main
echo "   - Código atualizado para: $(git log -1 --format='%h - %s')"
echo ""

# PASSO 2: Verificar arquivo crítico
echo "🔍 PASSO 2: Verificando código corrigido..."
if grep -q "from app.models import User" backend/app/auth_routes_multitenant.py; then
    echo "   ✅ Import correto encontrado: from app.models import User"
else
    echo "   ❌ ERRO: Import circular ainda presente!"
    echo "   Execute: grep 'from app' backend/app/auth_routes_multitenant.py"
    exit 1
fi
echo ""

# PASSO 3: Derrubar containers
echo "🛑 PASSO 3: Parando containers..."
docker compose -f docker-compose.prod.yml down
echo "   ✅ Containers parados"
echo ""

# PASSO 4: Rebuild forçado
echo "🔨 PASSO 4: Rebuilding imagem (sem cache)..."
echo "   ⏳ Isso pode levar alguns minutos..."
docker compose -f docker-compose.prod.yml build --no-cache backend
echo "   ✅ Imagem reconstruída"
echo ""

# PASSO 5: Subir serviços
echo "🚀 PASSO 5: Iniciando serviços..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d backend postgres
echo "   ✅ Containers iniciados"
echo ""

# PASSO 6: Aguardar inicialização
echo "⏳ PASSO 6: Aguardando inicialização (20s)..."
sleep 20
echo ""

# PASSO 7: Validar código no container
echo "🔍 PASSO 7: Validando código dentro do container..."
IMPORT_LINE=$(docker exec petshop-prod-backend head -20 app/auth_routes_multitenant.py | grep "from app.models import" || echo "")

if [ -n "$IMPORT_LINE" ]; then
    echo "   ✅ Import correto no container:"
    echo "   $IMPORT_LINE"
else
    echo "   ❌ ERRO: Import circular ainda presente no container!"
    docker exec petshop-prod-backend head -20 app/auth_routes_multitenant.py | grep "from app"
    exit 1
fi
echo ""

# PASSO 8: Verificar logs
echo "📋 PASSO 8: Verificando logs de inicialização..."
docker logs petshop-prod-backend --tail 30 | grep -E "(Started|Error|AttributeError|circular)" || echo "   ℹ️  Sem erros críticos nos logs"
echo ""

# PASSO 9: Verificar health
echo "🏥 PASSO 9: Verificando saúde dos containers..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep petshop
echo ""

# PASSO 10: Testar API
echo "🧪 PASSO 10: Testando endpoint de health..."
if curl -s http://localhost:8000/health | grep -q "ok"; then
    echo "   ✅ API respondendo corretamente"
else
    echo "   ⚠️  API não respondeu ou retornou erro"
    docker logs petshop-prod-backend --tail 10
fi
echo ""

echo "=============================="
echo "✅ DEPLOY CONCLUÍDO!"
echo ""
echo "📊 Status final:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo "🌐 Próximos passos:"
echo "   - Aguardar 1-2 minutos para health ficar 'healthy'"
echo "   - Configurar Nginx para expor na porta 80/443"
echo "   - Apontar domínio mlprohub.com.br"
echo ""
