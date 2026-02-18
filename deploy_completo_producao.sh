#!/bin/bash
# ============================================================================
# SCRIPT DE DEPLOY COMPLETO PARA PRODUÇÃO
# ============================================================================
# Este script executa TODAS as etapas necessárias para deploy em produção:
# 1. Commit e push do código
# 2. Conexão SSH ao servidor
# 3. Pull do código no servidor
# 4. Aplicação de migrations via Alembic
# 5. Importação dos dados do SimplesVet
#
# ATENÇÃO: Revise este script ANTES de executar!
# ============================================================================

set -e  # Para na primeira falha

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SERVER_IP="192.241.150.121"
SERVER_USER="root"
SERVER_PATH="/opt/petshop"

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  DEPLOY COMPLETO PARA PRODUÇÃO - PETSHOP  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# ETAPA 1: COMMIT LOCAL E PUSH  
# ============================================================================
echo -e "${YELLOW}[ETAPA 1/5] Commitando alterações locais...${NC}"
git add backend/app/produtos_models.py
git add backend/app/models.py
git add backend/alembic/versions/20260218_aumentar_codigo_barras.py
git add backend/importar_simplesvet.py

git commit -m "feat: aumentar codigo_barras para VARCHAR(20) + desabilitar FKs temporários

- Aumenta coluna produtos.codigo_barras de VARCHAR(13) para VARCHAR(20)
  para suportar EAN-14 e outros formatos
- Migration Alembic: 20260218_aumentar_codigo_barras.py
- Desabilita 6 ForeignKeys em produtos_models.py (tabelas não existem)
- Desabilita IA relationships em models.py (dependências circulares)
- Importador SimplesVet pronto para banco zerado de produção"

echo -e "${GREEN}✅ Commit criado!${NC}"

echo -e "${YELLOW}Enviando para GitHub...${NC}"
git push origin main
echo -e "${GREEN}✅ Push concluído!${NC}"
echo ""

# ============================================================================
# ETAPA 2: CONEXÃO SSH E PULL NO SERVIDOR
# ============================================================================
echo -e "${YELLOW}[ETAPA 2/5] Conectando ao servidor ${SERVER_IP}...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

echo "🔄 Acessando diretório do projeto..."
cd /opt/petshop

echo "📥 Fazendo pull do código..."
git pull origin main

echo "✅ Código atualizado no servidor!"
ENDSSH

echo -e "${GREEN}✅ Pull concluído no servidor!${NC}"
echo ""

# ============================================================================
# ETAPA 3: APLICAR MIGRATIONS VIA ALEMBIC
# ============================================================================
echo -e "${YELLOW}[ET APA 3/5] Aplicando migrations no banco de produção...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

cd /opt/petshop

echo "🗄️  Aplicando migrations com Alembic..."
docker-compose exec -T backend alembic upgrade head

echo "✅ Migrations aplicadas!"

echo "📊 Verificando versão atual do Alembic..."
docker-compose exec -T backend alembic current

ENDSSH

echo -e "${GREEN}✅ Migrations aplicadas em produção!${NC}"
echo ""

# ============================================================================
# ETAPA 4: IMPORTAR DADOS DO SIMPLESVET (FASE 1 e 2 - CADASTROS BÁSICOS)
# ============================================================================
echo -e "${YELLOW}[ETAPA 4/5] Importando cadastros básicos do SimplesVet...${NC}"
echo -e "${YELLOW}📋 FASE 1: Espécies e Raças${NC}"
echo -e "${YELLOW}📋 FASE 2: Clientes, Marcas e Produtos${NC}"
echo -e "${RED}⚠️  ATENÇÃO: Importação pode levar 5-10 minutos!${NC}"
echo ""

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

cd /opt/petshop

echo "════════════════════════════════════════════════════════"
echo "  FASE 1: CADASTROS BASE (Espécies, Raças)"
echo "════════════════════════════════════════════════════════"
docker-compose exec -T backend python importar_simplesvet.py --fase 1 --limite 20000

echo ""
echo "════════════════════════════════════════════════════════"
echo "  FASE 2: CLIENTES, MARCAS E PRODUTOS"
echo "════════════════════════════════════════════════════════"
docker-compose exec -T backend python importar_simplesvet.py --fase 2 --limite 10000

echo ""
echo "✅ Cadastros básicos importados com sucesso!"
echo ""
echo "ℹ️  PRÓXIMOS PASSOS (executar manualmente depois):"
echo "   - Fase 3: Importar Pets (vinculados aos clientes)"
echo "   - Fase 4: Importar Vendas e Histórico"

ENDSSH

echo -e "${GREEN}✅ Cadastros básicos do SimplesVet importados!${NC}"
echo -e "${YELLOW}ℹ️  Fases 3 e 4 (pets, vendas) serão importadas posteriormente${NC}"
echo ""

# ============================================================================
# ETAPA 5: VERIFICAÇÃO FINAL
# ============================================================================
echo -e "${YELLOW}[ETAPA 5/5] Verificando resultados...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

cd /opt/petshop

echo "📊 Contando cadastros básicos importados..."
docker-compose exec -T backend python -c "
from app.db.session import SessionLocal
from app.produtos_models import Produto, Marca, Categoria
from app.models import Cliente, Especie, Raca
from sqlalchemy import func

db = SessionLocal()

total_especies = db.query(func.count(Especie.id)).scalar()
total_racas = db.query(func.count(Raca.id)).scalar()
total_clientes = db.query(func.count(Cliente.id)).scalar()
total_marcas = db.query(func.count(Marca.id)).scalar()
total_produtos = db.query(func.count(Produto.id)).scalar()

print('')
print('═══════════════════════════════════════════════════════')
print('        CADASTROS BÁSICOS IMPORTADOS COM SUCESSO       ')
print('═══════════════════════════════════════════════════════')
print(f'  ✅ Espécies:  {total_especies:>6}')
print(f'  ✅ Raças:     {total_racas:>6}')
print(f'  ✅ Clientes:  {total_clientes:>6}')
print(f'  ✅ Marcas:    {total_marcas:>6}')
print(f'  ✅ Produtos:  {total_produtos:>6}')
print('═══════════════════════════════════════════════════════')
print('')
print('ℹ️  PENDENTE (importar depois):')
print('   - Pets (cadastros de animais)')
print('   - Vendas (histórico de vendas)')
print('   - Atendimentos (consultas veterinárias)')
print('')

db.close()
"

ENDSSH

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      🎉 DEPLOY CONCLUÍDO COM SUCESSO! 🎉     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ CADASTROS BÁSICOS IMPORTADOS:${NC}"
echo -e "   - Espécies, Raças, Clientes, Marcas, Produtos"
echo ""
echo -e "${YELLOW}📋 PRÓXIMOS PASSOS (importar manualmente):${NC}"
echo -e "   1. Testar Fase 3 em DEV (Pets)"
echo -e "   2. Testar Fase 4 em DEV (Vendas + Histórico)"
echo -e "   3. Executar Fase 3 e 4 em produção quando testado"
echo ""
echo -e "🌐 Sistema disponível em: ${GREEN}http://${SERVER_IP}${NC}"
echo ""
