#!/bin/bash

# ==============================================
# SCRIPT DE DEPLOY - PET SHOP PRO
# ==============================================

set -e  # Exit on error

echo "🚀 Iniciando deploy do Pet Shop Pro..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 1. GIT PULL
# ============================================
echo -e "${YELLOW}📥 Atualizando código do repositório...${NC}"
git pull origin main
echo -e "${GREEN}✅ Código atualizado${NC}"
echo ""

# ============================================
# 2. BACKUP DO BANCO
# ============================================
echo -e "${YELLOW}💾 Criando backup do banco de dados...${NC}"
BACKUP_DIR="/opt/backups/petshop"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

if docker ps | grep -q petshop-prod-postgres; then
    docker exec petshop-prod-postgres pg_dump -U petshop_admin petshop_prod | gzip > $BACKUP_DIR/pre_deploy_$DATE.sql.gz
    echo -e "${GREEN}✅ Backup criado: pre_deploy_$DATE.sql.gz${NC}"
else
    echo -e "${YELLOW}⚠️  Container postgres não encontrado, pulando backup${NC}"
fi
echo ""

# ============================================
# 3. BUILD DAS NOVAS IMAGENS
# ============================================
echo -e "${YELLOW}🔨 Construindo novas imagens Docker...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache
echo -e "${GREEN}✅ Imagens construídas${NC}"
echo ""

# ============================================
# 4. RODAR MIGRATIONS
# ============================================
echo -e "${YELLOW}🗄️  Executando migrations do banco...${NC}"
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
echo -e "${GREEN}✅ Migrations concluídas${NC}"
echo ""

# ============================================
# 5. REINICIAR SERVIÇOS (ZERO DOWNTIME)
# ============================================
echo -e "${YELLOW}🔄 Reiniciando serviços...${NC}"

# Backend
echo "  → Reiniciando backend..."
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps backend
sleep 5  # Aguardar inicialização

# Frontend
echo "  → Reiniciando frontend..."
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps frontend
sleep 2

# Nginx (último para evitar downtime)
echo "  → Reiniciando nginx..."
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps nginx
sleep 2

echo -e "${GREEN}✅ Serviços reiniciados${NC}"
echo ""

# ============================================
# 6. VERIFICAÇÃO DE SAÚDE
# ============================================
echo -e "${YELLOW}🏥 Verificando saúde dos serviços...${NC}"

# Aguardar containers ficarem healthy
echo "  → Aguardando containers..."
sleep 10

# Status dos containers
echo ""
echo "📊 Status dos serviços:"
docker compose -f docker-compose.prod.yml ps

echo ""

# Health check do backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend: Healthy${NC}"
else
    echo -e "${RED}❌ Backend: Erro no health check${NC}"
fi

# Health check do frontend via nginx
if curl -f -k https://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend: Healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend: Verificar manualmente${NC}"
fi

echo ""

# ============================================
# 7. LOGS RECENTES
# ============================================
echo -e "${YELLOW}📋 Últimas 20 linhas dos logs:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f docker-compose.prod.yml logs --tail=20
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# 8. FINALIZAÇÃO
# ============================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                            ║${NC}"
echo -e "${GREEN}║   ✅ DEPLOY CONCLUÍDO COM SUCESSO!        ║${NC}"
echo -e "${GREEN}║                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "🔍 Monitoramento:"
echo "   • Logs em tempo real: docker compose -f docker-compose.prod.yml logs -f"
echo "   • Status: docker compose -f docker-compose.prod.yml ps"
echo "   • Stats: docker stats"
echo ""
echo "📊 Acesso:"
echo "   • Frontend: https://mlprohub.com.br"
echo "   • API: https://mlprohub.com.br/api"
echo ""
echo "💾 Backup criado em: $BACKUP_DIR/pre_deploy_$DATE.sql.gz"
echo ""
echo "🎉 Sistema atualizado e rodando!"
