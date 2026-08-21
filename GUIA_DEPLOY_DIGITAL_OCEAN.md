# 🚀 Guia de Deploy - Digital Ocean

> Documento historico da primeira infraestrutura. Para a operacao atual, use
> `docs/PRODUCAO_DEPLOY_SSH.md`. Nao execute os comandos abaixo em um servidor
> atual sem uma revisao especifica e autorizacao operacional.

## 📋 Visão Geral

Substituir sistema atual em **mlprohub.com.br** pelo **Sistema Pet Shop Pro**.

### Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────┐
│                  mlprohub.com.br                        │
│              (Digital Ocean Droplet)                    │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
    ┌─────▼─────┐                  ┌─────▼─────┐
    │ Loja 1    │                  │ Loja 2+   │
    │ (Matriz)  │                  │ (Filiais) │
    ├───────────┤                  ├───────────┤
    │ ✅ Local  │                  │ ❌ Local  │
    │ ✅ Online │                  │ ✅ Online │
    └───────────┘                  └───────────┘
```

**Modelo Multi-Tenant:**
- Cada loja = 1 tenant
- Banco de dados compartilhado
- Dados isolados por tenant_id
- Autenticação JWT

---

## 🎯 Sugestões de Nomes de Domínio

### 🏆 Top 5 Recomendados

1. **petshoppro.com.br**
   - ✅ Direto e profissional
   - ✅ Fácil de lembrar
   - ✅ SEO friendly
   - 💰 ~R$ 40/ano

2. **sistemapet.com.br**
   - ✅ Descreve o produto
   - ✅ Marca própria
   - ✅ Genérico mas eficaz
   - 💰 ~R$ 40/ano

3. **petgestao.com.br**
   - ✅ Foco em gestão
   - ✅ Diferenciado
   - ✅ Profissional
   - 💰 ~R$ 40/ano

4. **smartpetshop.com.br**
   - ✅ Moderno (Smart/IA)
   - ✅ Atrativo
   - ✅ Tech-forward
   - 💰 ~R$ 40/ano

5. **petmanager.com.br**
   - ✅ Internacional
   - ✅ Gerencial
   - ✅ Escalável
   - 💰 ~R$ 40/ano

### 🌟 Opções Premium

- **petpro.app** - Moderno, app-focused (R$ 150/ano)
- **mypetshop.com.br** - Personalizado (R$ 40/ano)
- **petcloud.com.br** - Cloud-first (R$ 60/ano)
- **nexuspet.com.br** - Tech/Premium (R$ 80/ano)

### 💡 Considerações

**O que seu sistema oferece:**
- ✅ Gestão Completa (PDV, Estoque, Financeiro)
- ✅ Multi-Tenancy (várias lojas)
- ✅ IA (Classificação Inteligente de Rações)
- ✅ Análises Avançadas (Margem, ROI, Previsão)
- ✅ Integrações (Cartões, Importações)
- ✅ Cloud + Local

**Nome ideal deve ter:**
- Fácil pronúncia
- Curto (máx 15 chars)
- Relacionado a pet shop
- Sugestão de tecnologia/profissionalismo
- Disponível em .com.br

**Minha Recomendação #1:** `petshoppro.com.br`
- Direto ao ponto
- Profissional
- Memorável
- SEO ótimo

---

## 🛠️ Preparação do Deploy

### 1. Requisitos do Servidor (Digital Ocean)

**Droplet Recomendado:**
```
- CPU: 2 vCPUs (mínimo)
- RAM: 4 GB (recomendado 8 GB)
- SSD: 80 GB
- SO: Ubuntu 22.04 LTS
- Região: São Paulo (latência menor)
- Custo: ~$24/mês (4GB) ou ~$48/mês (8GB)
```

**Software Necessário:**
- Docker 24+
- Docker Compose 2.20+
- Nginx (reverse proxy)
- Certbot (SSL/HTTPS)
- PostgreSQL 14+ (via Docker)

---

## 📦 Passo 1: Preparar Arquivos de Produção

### 1.1 Criar docker-compose.prod.yml

Vou criar um arquivo otimizado para produção com todas as configurações necessárias.

```yaml
version: '3.8'

services:
  # ========================================
  # POSTGRESQL - BANCO DE DADOS PRODUÇÃO
  # ========================================
  postgres:
    image: postgres:14-alpine
    container_name: petshop-prod-postgres
    restart: always
    environment:
      POSTGRES_DB: petshop_prod
      POSTGRES_USER: petshop_admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Definir no .env
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - petshop-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U petshop_admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ========================================
  # BACKEND - API FASTAPI
  # ========================================
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: petshop-prod-backend
    restart: always
    environment:
      # Database
      DATABASE_URL: postgresql://petshop_admin:${POSTGRES_PASSWORD}@postgres:5432/petshop_prod
      
      # Security
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 1440
      
      # Environment
      ENVIRONMENT: production
      DEBUG: "false"
      
      # CORS
      CORS_ORIGINS: https://mlprohub.com.br,https://www.mlprohub.com.br
      
      # App
      APP_NAME: "Pet Shop Pro"
      APP_VERSION: "1.1.0"
      
      # Timezone
      TZ: America/Sao_Paulo
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/logs:/app/logs
      - ./backend/data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - petshop-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ========================================
  # FRONTEND - REACT + VITE
  # ========================================
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        VITE_API_URL: https://mlprohub.com.br/api
    container_name: petshop-prod-frontend
    restart: always
    networks:
      - petshop-network

  # ========================================
  # NGINX - REVERSE PROXY
  # ========================================
  nginx:
    image: nginx:alpine
    container_name: petshop-prod-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
      - frontend
    networks:
      - petshop-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local

networks:
  petshop-network:
    driver: bridge
```

### 1.2 Criar .env.production

```bash
# Database
POSTGRES_PASSWORD=SUA_SENHA_SUPER_FORTE_AQUI_123!@#

# JWT
JWT_SECRET=SUA_CHAVE_JWT_SUPER_SECRETA_MUDE_ISSO_789$%^

# App
APP_ENV=production
DEBUG=false

# Domain
DOMAIN=mlprohub.com.br

# Email (futuro)
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
```

### 1.3 Criar Dockerfile.prod para Backend

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p /app/uploads /app/logs /app/data

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 1.4 Criar Dockerfile.prod para Frontend

```dockerfile
# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependências
RUN npm ci

# Copiar código
COPY . .

# Build argument para API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build da aplicação
RUN npm run build

# Stage 2: Servir com Nginx
FROM nginx:alpine

# Copiar build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuração nginx customizada (se houver)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expor porta
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### 1.5 Criar nginx.conf

```nginx
upstream backend {
    server backend:8000;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name mlprohub.com.br www.mlprohub.com.br;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name mlprohub.com.br www.mlprohub.com.br;
    
    # SSL Certificates
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend - React App
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Backend API
    location /api {
        rewrite ^/api(.*)$ $1 break;
        proxy_pass http://backend;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Upload size
        client_max_body_size 50M;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## 🚀 Passo 2: Deploy no Digital Ocean

### 2.1 Conectar ao Servidor

```bash
ssh root@SEU_IP_DO_DROPLET
```

### 2.2 Instalar Docker

```bash
# Atualizar sistema
apt update && apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
apt install docker-compose-plugin -y

# Verificar instalação
docker --version
docker compose version
```

### 2.3 Preparar Diretórios

```bash
# Criar estrutura
mkdir -p /opt/petshop
cd /opt/petshop

# Clonar repositório
git clone https://github.com/SEU_USUARIO/Sistema-Pet.git .

# Criar diretórios necessários
mkdir -p nginx/ssl
mkdir -p backend/uploads
mkdir -p backend/logs
mkdir -p backend/data
```

### 2.4 Configurar Variáveis de Ambiente

```bash
# Copiar exemplo
cp .env.example .env.production

# Editar com nano ou vim
nano .env.production

# Gerar senhas fortes
# Postgres Password:
openssl rand -base64 32

# JWT Secret:
openssl rand -hex 64
```

### 2.5 Configurar SSL/HTTPS (Certbot)

```bash
# Instalar Certbot
apt install certbot python3-certbot-nginx -y

# Obter certificado
certbot certonly --standalone -d mlprohub.com.br -d www.mlprohub.com.br

# Certificados ficam em:
# /etc/letsencrypt/live/mlprohub.com.br/

# Copiar para nginx
cp /etc/letsencrypt/live/mlprohub.com.br/fullchain.pem /opt/petshop/nginx/ssl/
cp /etc/letsencrypt/live/mlprohub.com.br/privkey.pem /opt/petshop/nginx/ssl/

# Renovação automática (crontab)
crontab -e
# Adicionar linha:
0 0 * * * certbot renew --quiet
```

### 2.6 Build e Start

```bash
# Build das imagens
docker compose -f docker-compose.prod.yml build

# Iniciar serviços
docker compose -f docker-compose.prod.yml up -d

# Verificar status
docker compose -f docker-compose.prod.yml ps

# Ver logs
docker compose -f docker-compose.prod.yml logs -f
```

### 2.7 Rodar Migrations

```bash
# Executar migrations do Alembic
docker exec petshop-prod-backend alembic upgrade head

# Criar tenant inicial (se necessário)
docker exec -it petshop-prod-backend python -c "
from app.db.session import SessionLocal
from app.models import Tenant
db = SessionLocal()
tenant = Tenant(nome='Matriz', ativo=True)
db.add(tenant)
db.commit()
print(f'Tenant criado: {tenant.id}')
"
```

---

## 🔧 Passo 3: Configurações Adicionais

### 3.1 Firewall

```bash
# Configurar UFW
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw enable
ufw status
```

### 3.2 Backup Automático

```bash
# Criar script de backup
cat > /opt/backup-petshop.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/petshop"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco
docker exec petshop-prod-postgres pg_dump -U petshop_admin petshop_prod | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup dos uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C /opt/petshop/backend uploads

# Manter apenas últimos 7 dias
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
EOF

chmod +x /opt/backup-petshop.sh

# Agendar backup diário (3h da manhã)
crontab -e
# Adicionar:
0 3 * * * /opt/backup-petshop.sh >> /var/log/petshop-backup.log 2>&1
```

### 3.3 Monitoramento

```bash
# Instalar Netdata (opcional)
bash <(curl -Ss https://my-netdata.io/kickstart.sh)

# Acesso: http://SEU_IP:19999
```

---

## 📊 Passo 4: Verificação e Testes

### 4.1 Health Checks

```bash
# Backend
curl https://mlprohub.com.br/api/health

# Containers
docker compose -f docker-compose.prod.yml ps

# Logs
docker compose -f docker-compose.prod.yml logs --tail=50
```

### 4.2 Teste de Acesso

1. Abrir navegador: `https://mlprohub.com.br`
2. Verificar certificado SSL (cadeado verde)
3. Fazer login
4. Testar funcionalidades principais

### 4.3 Performance

```bash
# CPU/Memória
docker stats --no-stream

# Disco
df -h

# Rede
netstat -an | grep :443 | wc -l
```

---

## 🔄 Passo 5: Atualização do Sistema

### Script de Deploy (deploy.sh)

```bash
#!/bin/bash

echo "🚀 Iniciando deploy do Pet Shop Pro..."

# Pull do repositório
git pull origin main

# Build das novas imagens
docker compose -f docker-compose.prod.yml build --no-cache

# Rodar migrations
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Reiniciar serviços (zero downtime com rolling update)
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps backend
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps frontend

echo "✅ Deploy concluído!"
echo "📊 Status dos serviços:"
docker compose -f docker-compose.prod.yml ps
```

**Uso:**
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 🏪 Configuração Multi-Loja

### Loja Matriz (Híbrido)

**Local (desenvolvimento):**
```bash
# Rodar docker-compose.local-dev.yml
docker-compose -f docker-compose.local-dev.yml up -d
# Acesso: http://localhost:5173
```

**Online (produção):**
```
# Usar credenciais da produção
https://mlprohub.com.br
```

### Lojas Filiais (Apenas Online)

**Configuração:**
```
URL: https://mlprohub.com.br
Tenant: Cada loja terá seu próprio tenant_id
Login: admin@loja2.com / senha
```

**Criar Tenants:**
```sql
-- No banco de produção
INSERT INTO tenants (nome, ativo, created_at) VALUES 
('Loja Matriz', true, NOW()),
('Loja Filial 1', true, NOW()),
('Loja Filial 2', true, NOW());
```

---

## 📝 Checklist Pós-Deploy

- [ ] SSL/HTTPS funcionando
- [ ] Backend respondendo (/health)
- [ ] Frontend carregando
- [ ] Login funcionando
- [ ] Tenants criados
- [ ] Usuários criados
- [ ] Backup configurado
- [ ] Monitoramento ativo
- [ ] Firewall configurado
- [ ] DNS apontando (mlprohub.com.br → IP do Droplet)

---

## 🆘 Troubleshooting

### Erro: "Connection refused"
```bash
# Verificar se backend está rodando
docker logs petshop-prod-backend

# Verificar rede
docker network inspect petshop_petshop-network
```

### Erro: "Database connection failed"
```bash
# Verificar Postgres
docker logs petshop-prod-postgres

# Testar conexão
docker exec -it petshop-prod-postgres psql -U petshop_admin -d petshop_prod
```

### Erro: "502 Bad Gateway"
```bash
# Verificar nginx
docker logs petshop-prod-nginx

# Verificar upstream
curl http://localhost:8000/health
```

---

## 📞 Suporte

**Documentação Completa:**
- Docker: https://docs.docker.com/
- Digital Ocean: https://docs.digitalocean.com/
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/

**Monitoramento Recomendado:**
- Uptime Robot (free): https://uptimerobot.com/
- Better Uptime: https://betteruptime.com/

---

**Desenvolvido com ❤️ para Pet Shop Pro**  
**Versão**: 1.1.0 (Deploy Guide)
