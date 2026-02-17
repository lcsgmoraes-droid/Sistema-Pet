# 🚨 CORREÇÃO IMEDIATA - SERVIDOR DE PRODUÇÃO

## ❌ Problema Detectado

1. **Arquivo `.env.production` no servidor está incompleto** (1307 bytes)
2. **Variáveis `POSTGRES_PASSWORD` e `JWT_SECRET_KEY` não estão sendo carregadas**
3. **Arquivo `Dockerfile.prod` do frontend pode estar faltando**

---

## ✅ SOLUÇÃO RÁPIDA (5 minutos)

### 1️⃣ No servidor, restaure o backup do .env.production:

```bash
cd /opt/petshop
cp .env.production.backup .env.production
```

**Se isso não funcionar, copie do seu computador local:**

### 2️⃣ No seu computador local, copie o arquivo para o servidor:

```powershell
# Via SCP (ajuste usuário e IP do seu servidor)
scp .env.production root@SEU_SERVIDOR_IP:/opt/petshop/.env.production
```

Ou manualmente:
- Abra o arquivo `.env.production` local
- Copie TODO o conteúdo
- No servidor, execute: `nano /opt/petshop/.env.production`
- Cole o conteúdo
- Salve com `Ctrl+X`, depois `Y`, depois `Enter`

---

### 3️⃣ Verifique se as variáveis estão corretas:

```bash
cd /opt/petshop
grep "POSTGRES_PASSWORD" .env.production
grep "JWT_SECRET_KEY" .env.production
grep "SQL_AUDIT_ENFORCE_LEVEL" .env.production
```

**Deve retornar:**
```
POSTGRES_PASSWORD=MUDE_ESTA_SENHA_AGORA_USE_SENHA_FORTE_2026
JWT_SECRET_KEY=QCELf4vxUh44QDuxOx15UHyb6Zkav24Mlqipoy0MxLXW8ajbvEcEN_8QGjGIcgXv
SQL_AUDIT_ENFORCE_LEVEL=error
```

---

### 4️⃣ Envie os Dockerfiles para o servidor:

```bash
cd /opt/petshop

# Verificar se existem
ls -la frontend/Dockerfile.prod
ls -la backend/Dockerfile.prod
```

**Se não existirem, faça git pull:**

```bash
cd /opt/petshop
git pull origin main
```

---

### 5️⃣ Execute o deploy completo:

```bash
cd /opt/petshop
chmod +x EXECUTAR_NO_SERVIDOR.sh
./EXECUTAR_NO_SERVIDOR.sh
```

Ou manualmente:

```bash
cd /opt/petshop

# Parar containers
docker compose -f docker-compose.prod.yml down

# Iniciar com build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Aguardar 10 segundos
sleep 10

# Verificar status
docker compose -f docker-compose.prod.yml ps

# Aplicar migrations
docker exec petshop-prod-backend bash -c "cd /app && alembic upgrade head"

# Verificar SQL_AUDIT
docker exec petshop-prod-backend env | grep SQL_AUDIT
```

---

## 🔍 Verificação Final

Execute no servidor:

```bash
# 1. Containers devem estar rodando
docker compose -f docker-compose.prod.yml ps

# 2. SQL_AUDIT deve ser 'error'
docker exec petshop-prod-backend env | grep SQL_AUDIT_ENFORCE_LEVEL

# 3. Logs não devem ter erro de SQL_AUDIT
docker logs petshop-prod-backend | grep -i "sql_audit"

# 4. Health check deve funcionar
curl http://localhost:8000/health
```

---

## ⚠️ Se ainda der erro

### Opção A: Criar .env.production manualmente no servidor

```bash
cd /opt/petshop
nano .env.production
```

Cole este conteúdo mínimo:

```env
# Ambiente
ENVIRONMENT=production
DEBUG=false

# Banco de Dados
POSTGRES_USER=petshop_admin
POSTGRES_PASSWORD=SUA_SENHA_FORTE_AQUI
POSTGRES_DB=petshop_prod
DATABASE_URL=postgresql://petshop_admin:SUA_SENHA_FORTE_AQUI@postgres:5432/petshop_prod

# Segurança
JWT_SECRET_KEY=QCELf4vxUh44QDuxOx15UHyb6Zkav24Mlqipoy0MxLXW8ajbvEcEN_8QGjGIcgXv

# SQL Audit
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=error
```

Salve e rode novamente o deploy.

---

## 📞 Suporte

Se o problema persistir, envie:

```bash
# Conteúdo do .env.production (sem senhas!)
cat .env.production | grep -v PASSWORD | grep -v SECRET

# Status dos containers
docker compose -f docker-compose.prod.yml ps

# Logs do backend
docker logs --tail=50 petshop-prod-backend
```
