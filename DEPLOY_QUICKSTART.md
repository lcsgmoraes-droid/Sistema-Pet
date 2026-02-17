# 🚀 Guia Rápido - Deploy Digital Ocean

## ⚡ Quick Start (10 minutos)

### 1. Criar Droplet Digital Ocean
- **SO**: Ubuntu 22.04 LTS
- **RAM**: 4 GB (recomendado 8 GB)
- **Região**: São Paulo
- **IP**: Anotar IP público

### 2. Configurar DNS
```
Tipo: A
Nome: @
Valor: SEU_IP_DO_DROPLET

Tipo: A  
Nome: www
Valor: SEU_IP_DO_DROPLET
```
**Aguardar propagação (~5-60 min)**

### 3. Conectar ao Servidor
```bash
ssh root@SEU_IP

# Fazer upload do script
# No seu PC:
scp setup-server.sh root@SEU_IP:/root/

# No servidor:
bash setup-server.sh
```

### 4. Clonar Repositório
```bash
cd /opt/petshop
git clone https://github.com/lcsgmoraes-droid/Sistema-Pet.git .
```

### 5. Configurar Environment
```bash
cp .env.production.example .env.production
nano .env.production

# Gerar senhas:
POSTGRES_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -hex 64)

# Copiar e colar no arquivo
```

### 6. Obter SSL (Certbot)
```bash
# Certificado Let's Encrypt
certbot certonly --standalone \
  -d mlprohub.com.br \
  -d www.mlprohub.com.br

# Copiar certificados
cp /etc/letsencrypt/live/mlprohub.com.br/fullchain.pem /opt/petshop/nginx/ssl/
cp /etc/letsencrypt/live/mlprohub.com.br/privkey.pem /opt/petshop/nginx/ssl/
```

### 7. Build & Deploy
```bash
cd /opt/petshop

# Build
docker compose -f docker-compose.prod.yml build

# Start
docker compose -f docker-compose.prod.yml up -d

# Migrations
docker exec petshop-prod-backend alembic upgrade head

# Verificar
docker compose -f docker-compose.prod.yml ps
```

### 8. Verificar
```bash
# Status
docker-stats-petshop

# Health checks
curl http://localhost:8000/health
curl -k https://localhost/health

# Abrir navegador
# https://mlprohub.com.br
```

---

## 📋 Checklist de Deploy

- [ ] Droplet criado (Ubuntu 22.04, 4GB+)
- [ ] DNS configurado e propagado
- [ ] SSH funcionando
- [ ] Script setup-server.sh executado
- [ ] Repositório clonado
- [ ] .env.production configurado
- [ ] SSL obtido e copiado
- [ ] Build concluído
- [ ] Containers rodando
- [ ] Migrations executadas
- [ ] Health checks OK
- [ ] Site acessível via HTTPS

---

## 🔧 Comandos Úteis

```bash
# Ver status
docker-stats-petshop

# Logs em tempo real
docker compose -f docker-compose.prod.yml logs -f

# Logs de um serviço específico
docker compose -f docker-compose.prod.yml logs -f backend

# Restart de um serviço
docker compose -f docker-compose.prod.yml restart backend

# Parar tudo
docker compose -f docker-compose.prod.yml down

# Iniciar tudo
docker compose -f docker-compose.prod.yml up -d

# Backup manual
/opt/backup-petshop.sh

# Limpeza Docker
/opt/cleanup-docker.sh

# Ver disco
df -h

# Ver RAM/CPU
htop
```

---

## 🆘 Troubleshooting Rápido

### ❌ Erro: "Connection refused"
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend
```

### ❌ Erro: "502 Bad Gateway"
```bash
# Backend não está respondendo
docker exec -it petshop-prod-backend curl http://localhost:8000/health
docker compose -f docker-compose.prod.yml restart backend
```

### ❌ Erro: "Database connection failed"
```bash
docker logs petshop-prod-postgres
docker exec -it petshop-prod-postgres psql -U petshop_admin -d petshop_prod -c "SELECT 1;"
```

### ❌ SSL não funciona
```bash
# Verificar certificados
ls -la /opt/petshop/nginx/ssl/

# Renovar certificado
certbot renew

# Copiar novamente
cp /etc/letsencrypt/live/mlprohub.com.br/*.pem /opt/petshop/nginx/ssl/

# Restart nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### ❌ Frontend não carrega
```bash
# Verificar build do frontend
docker exec petshop-prod-frontend ls -la /usr/share/nginx/html/

# Rebuild frontend
docker compose -f docker-compose.prod.yml up -d --build frontend
```

---

## 🔄 Atualizar Sistema

```bash
cd /opt/petshop
chmod +x deploy.sh
./deploy.sh
```

**Ou manualmente:**
```bash
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 💾 Backup & Restore

### Fazer Backup
```bash
/opt/backup-petshop.sh

# Ou manual:
docker exec petshop-prod-postgres pg_dump -U petshop_admin petshop_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restaurar Backup
```bash
gunzip < backup_20260214.sql.gz | docker exec -i petshop-prod-postgres psql -U petshop_admin petshop_prod
```

### Download Backup para PC
```bash
# No seu PC:
scp root@SEU_IP:/opt/backups/petshop/db_*.sql.gz ./
```

---

## 📊 Monitoramento

### Verificar Saúde
```bash
# Containers
docker compose -f docker-compose.prod.yml ps

# Recursos
docker stats --no-stream

# Disco
df -h

# Memória
free -h

# CPU
top

# Logs de erro
docker compose -f docker-compose.prod.yml logs --tail=100 | grep -i error
```

### Logs Importantes
```bash
# Logs do backend
tail -f /opt/petshop/backend/logs/app.log

# Logs do nginx
docker logs petshop-prod-nginx

# Logs de backup
tail -f /var/log/petshop/backup.log

# Logs de limpeza
tail -f /var/log/petshop/cleanup.log
```

---

## 🔐 Segurança

### Alterar Senha SSH
```bash
passwd
```

### Ver Tentativas de Login Bloqueadas
```bash
fail2ban-client status sshd
```

### Ver Firewall
```bash
ufw status verbose
```

### Renovar SSL (manual)
```bash
certbot renew
cp /etc/letsencrypt/live/mlprohub.com.br/*.pem /opt/petshop/nginx/ssl/
docker compose -f docker-compose.prod.yml restart nginx
```

---

## 📞 Suporte

### Documentação Completa
- [GUIA_DEPLOY_DIGITAL_OCEAN.md](GUIA_DEPLOY_DIGITAL_OCEAN.md) - Guia detalhado
- [SUGESTOES_NOMES_DOMINIO.md](SUGESTOES_NOMES_DOMINIO.md) - Sugestões de domínio

### Verificar Versões
```bash
# Docker
docker --version

# Docker Compose
docker compose version

# Sistema
lsb_release -a

# Aplicação
docker exec petshop-prod-backend python -c "from app.main import app; print(app.version)"
```

---

## ⚙️ Variáveis de Ambiente Principais

```bash
# .env.production
POSTGRES_PASSWORD=...        # Senha do banco
JWT_SECRET=...               # Chave JWT
DOMAIN=mlprohub.com.br       # Seu domínio
CORS_ORIGINS=https://...     # CORS permitido
```

---

## 🎯 Próximos Passos Após Deploy

1. ✅ **Criar primeiro usuário admin** via backend
2. ✅ **Configurar tenants** (lojas)
3. ✅ **Importar dados** (se houver)
4. ✅ **Testar funcionalidades** principais
5. ✅ **Configurar backups externos** (opcional)
6. ✅ **Configurar monitoramento** (UptimeRobot, etc)
7. ✅ **Testar em diferentes dispositivos**
8. ✅ **Treinar usuários**

---

## 🏪 Multi-Loja Setup

### Loja Matriz (Híbrido)
```bash
# Local
docker-compose -f docker-compose.local-dev.yml up -d

# Online
https://mlprohub.com.br
```

### Lojas Filiais (Apenas Online)
```
URL: https://mlprohub.com.br
Tenant: Auto-selecionado no login
```

### Criar Tenant
```sql
-- No banco de produção
INSERT INTO tenants (nome, ativo, created_at) 
VALUES ('Loja Filial 1', true, NOW());
```

---

**Última atualização**: 14/02/2026  
**Versão**: 1.0.0
