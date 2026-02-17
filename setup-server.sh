#!/bin/bash

# ==============================================
# SCRIPT DE CONFIGURAÇÃO INICIAL - DIGITAL OCEAN
# ==============================================
# Execute este script no servidor Digital Ocean
# após criar o droplet pela primeira vez
# ==============================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║                                                ║"
echo "║   🚀 PET SHOP PRO - SETUP INICIAL             ║"
echo "║      Digital Ocean Ubuntu 22.04                ║"
echo "║                                                ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ============================================
# 1. VERIFICAR SE É ROOT
# ============================================
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}❌ Execute como root: sudo bash setup-server.sh${NC}"
   exit 1
fi

echo -e "${GREEN}✅ Executando como root${NC}"
echo ""

# ============================================
# 2. ATUALIZAR SISTEMA
# ============================================
echo -e "${YELLOW}📦 Atualizando sistema...${NC}"
apt update
apt upgrade -y
apt autoremove -y
echo -e "${GREEN}✅ Sistema atualizado${NC}"
echo ""

# ============================================
# 3. INSTALAR DEPENDÊNCIAS BÁSICAS
# ============================================
echo -e "${YELLOW}📦 Instalando dependências...${NC}"
apt install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban
echo -e "${GREEN}✅ Dependências instaladas${NC}"
echo ""

# ============================================
# 4. INSTALAR DOCKER
# ============================================
echo -e "${YELLOW}🐳 Instalando Docker...${NC}"

# Remover versões antigas se existirem
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Adicionar repositório oficial do Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Iniciar e habilitar Docker
systemctl start docker
systemctl enable docker

# Verificar instalação
docker --version
docker compose version

echo -e "${GREEN}✅ Docker instalado${NC}"
echo ""

# ============================================
# 5. INSTALAR CERTBOT (SSL)
# ============================================
echo -e "${YELLOW}🔒 Instalando Certbot...${NC}"
apt install -y certbot python3-certbot-nginx
echo -e "${GREEN}✅ Certbot instalado${NC}"
echo ""

# ============================================
# 6. CONFIGURAR FIREWALL (UFW)
# ============================================
echo -e "${YELLOW}🔥 Configurando firewall...${NC}"

# Configurar regras
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Habilitar UFW
ufw --force enable

echo -e "${GREEN}✅ Firewall configurado${NC}"
ufw status
echo ""

# ============================================
# 7. CONFIGURAR FAIL2BAN (SEGURANÇA SSH)
# ============================================
echo -e "${YELLOW}🛡️  Configurando Fail2Ban...${NC}"

# Criar configuração local
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
destemail = root@localhost
sendername = Fail2Ban
action = %(action_mwl)s

[sshd]
enabled = true
port = 22
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

# Reiniciar Fail2Ban
systemctl restart fail2ban
systemctl enable fail2ban

echo -e "${GREEN}✅ Fail2Ban configurado${NC}"
echo ""

# ============================================
# 8. CRIAR ESTRUTURA DE DIRETÓRIOS
# ============================================
echo -e "${YELLOW}📁 Criando estrutura de diretórios...${NC}"

# Diretório principal
mkdir -p /opt/petshop
mkdir -p /opt/backups/petshop

# Nginx
mkdir -p /opt/petshop/nginx/ssl

# Backend
mkdir -p /opt/petshop/backend/uploads
mkdir -p /opt/petshop/backend/logs
mkdir -p /opt/petshop/backend/data

# Logs do sistema
mkdir -p /var/log/petshop

# Permissões
chown -R root:root /opt/petshop
chmod -R 755 /opt/petshop

echo -e "${GREEN}✅ Estrutura criada${NC}"
echo ""

# ============================================
# 9. CONFIGURAR BACKUP AUTOMÁTICO
# ============================================
echo -e "${YELLOW}💾 Configurando backup automático...${NC}"

cat > /opt/backup-petshop.sh << 'BACKUP_SCRIPT'
#!/bin/bash
BACKUP_DIR="/opt/backups/petshop"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco
if docker ps | grep -q petshop-prod-postgres; then
    docker exec petshop-prod-postgres pg_dump -U petshop_admin petshop_prod | gzip > $BACKUP_DIR/db_$DATE.sql.gz
    echo "[$(date)] Backup do banco criado: db_$DATE.sql.gz" >> /var/log/petshop/backup.log
fi

# Backup dos uploads
if [ -d /opt/petshop/backend/uploads ]; then
    tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C /opt/petshop/backend uploads
    echo "[$(date)] Backup dos uploads criado: uploads_$DATE.tar.gz" >> /var/log/petshop/backup.log
fi

# Manter apenas últimos 7 dias
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +7 -delete

echo "[$(date)] Backup concluído. DB e Uploads salvos." >> /var/log/petshop/backup.log
BACKUP_SCRIPT

chmod +x /opt/backup-petshop.sh

# Adicionar ao crontab (3h da manhã, todo dia)
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/backup-petshop.sh") | crontab -

echo -e "${GREEN}✅ Backup automático configurado (diário às 3h)${NC}"
echo ""

# ============================================
# 10. OTIMIZAÇÕES DO SISTEMA
# ============================================
echo -e "${YELLOW}⚙️  Aplicando otimizações...${NC}"

# Aumentar limites de arquivos abertos
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
EOF

# Otimizações de rede
cat >> /etc/sysctl.conf << 'EOF'
# Network optimizations
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
net.ipv4.ip_local_port_range = 10000 65000
EOF

sysctl -p

echo -e "${GREEN}✅ Otimizações aplicadas${NC}"
echo ""

# ============================================
# 11. CONFIGURAR TIMEZONE
# ============================================
echo -e "${YELLOW}🌎 Configurando timezone...${NC}"
timedatectl set-timezone America/Sao_Paulo
echo -e "${GREEN}✅ Timezone: America/Sao_Paulo${NC}"
echo ""

# ============================================
# 12. INSTALAR FERRAMENTAS DE MONITORAMENTO
# ============================================
echo -e "${YELLOW}📊 Instalando ferramentas de monitoramento...${NC}"

# Docker stats script
cat > /usr/local/bin/docker-stats-petshop << 'STATS_SCRIPT'
#!/bin/bash
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐳 Pet Shop Pro - Status dos Containers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose -f /opt/petshop/docker-compose.prod.yml ps
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Uso de Recursos"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker stats --no-stream
STATS_SCRIPT

chmod +x /usr/local/bin/docker-stats-petshop

echo -e "${GREEN}✅ Comando 'docker-stats-petshop' criado${NC}"
echo ""

# ============================================
# 13. CRIAR SCRIPT DE MANUTENÇÃO
# ============================================
echo -e "${YELLOW}🔧 Criando scripts de manutenção...${NC}"

# Script de limpeza
cat > /opt/cleanup-docker.sh << 'CLEANUP_SCRIPT'
#!/bin/bash
echo "🧹 Limpando recursos Docker não utilizados..."
docker system prune -af --volumes
echo "✅ Limpeza concluída!"
CLEANUP_SCRIPT

chmod +x /opt/cleanup-docker.sh

# Agendar limpeza semanal (domingo 2h)
(crontab -l 2>/dev/null; echo "0 2 * * 0 /opt/cleanup-docker.sh >> /var/log/petshop/cleanup.log 2>&1") | crontab -

echo -e "${GREEN}✅ Manutenção automática configurada${NC}"
echo ""

# ============================================
# 14. INFORMAÇÕES FINAIS
# ============================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                ║${NC}"
echo -e "${BLUE}║   ✅ SERVIDOR CONFIGURADO COM SUCESSO!        ║${NC}"
echo -e "${BLUE}║                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}📋 RESUMO DA CONFIGURAÇÃO:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Sistema atualizado (Ubuntu 22.04)"
echo "✅ Docker instalado: $(docker --version | cut -d' ' -f3)"
echo "✅ Docker Compose: $(docker compose version | cut -d' ' -f4)"
echo "✅ Certbot instalado para SSL"
echo "✅ Firewall (UFW) ativo - Portas: 22, 80, 443"
echo "✅ Fail2Ban ativo (proteção SSH)"
echo "✅ Backup automático diário (3h)"
echo "✅ Limpeza automática semanal (domingo 2h)"
echo "✅ Timezone: America/Sao_Paulo"
echo ""

echo -e "${YELLOW}📁 ESTRUTURA CRIADA:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "/opt/petshop/              → Aplicação"
echo "/opt/backups/petshop/      → Backups"
echo "/var/log/petshop/          → Logs"
echo ""

echo -e "${YELLOW}🔧 COMANDOS ÚTEIS:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "docker-stats-petshop       → Ver status dos containers"
echo "/opt/backup-petshop.sh     → Fazer backup manual"
echo "/opt/cleanup-docker.sh     → Limpar recursos Docker"
echo "docker compose -f /opt/petshop/docker-compose.prod.yml logs -f"
echo "                           → Ver logs em tempo real"
echo ""

echo -e "${YELLOW}📝 PRÓXIMOS PASSOS:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  Clonar repositório:"
echo "    cd /opt/petshop"
echo "    git clone https://github.com/SeuUsuario/Sistema-Pet.git ."
echo ""
echo "2️⃣  Configurar variáveis de ambiente:"
echo "    cp .env.production.example .env.production"
echo "    nano .env.production"
echo "    # Gerar senhas:"
echo "    # POSTGRES_PASSWORD=\$(openssl rand -base64 32)"
echo "    # JWT_SECRET=\$(openssl rand -hex 64)"
echo ""
echo "3️⃣  Configurar SSL (ANTES de buildar):"
echo "    # Parar serviços na porta 80 se houver"
echo "    certbot certonly --standalone \\"
echo "      -d mlprohub.com.br \\"
echo "      -d www.mlprohub.com.br"
echo ""
echo "    # Copiar certificados"
echo "    cp /etc/letsencrypt/live/mlprohub.com.br/fullchain.pem \\"
echo "       /opt/petshop/nginx/ssl/"
echo "    cp /etc/letsencrypt/live/mlprohub.com.br/privkey.pem \\"
echo "       /opt/petshop/nginx/ssl/"
echo ""
echo "4️⃣  Buildar e iniciar:"
echo "    docker compose -f docker-compose.prod.yml build"
echo "    docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "5️⃣  Rodar migrations:"
echo "    docker exec petshop-prod-backend alembic upgrade head"
echo ""
echo "6️⃣  Verificar saúde:"
echo "    docker-stats-petshop"
echo "    curl https://mlprohub.com.br/health"
echo ""

echo -e "${GREEN}🎉 Servidor pronto para receber a aplicação!${NC}"
echo ""

# Exibir IP do servidor
IP=$(curl -s ifconfig.me)
echo -e "${BLUE}🌐 IP do servidor: $IP${NC}"
echo ""
echo -e "${YELLOW}⚠️  Configure o DNS do domínio apontando para este IP:${NC}"
echo "   Tipo A: @ → $IP"
echo "   Tipo A: www → $IP"
echo ""
