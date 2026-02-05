# 🎯 GUIA RÁPIDO - Ambientes Organizados

## 📌 Qual Ambiente Usar?

### 🔵 DESENVOLVIMENTO
- **Quando usar:** Programando, testando código, desenvolvendo features
- **Banco de dados:** SQLite (arquivo local, rápido)
- **Docker:** NÃO (roda direto no Windows)
- **Iniciar:** `INICIAR_DEV.bat`
- **Dados:** Teste/Mock (pode apagar e recriar)

### 🟢 PRODUÇÃO  
- **Quando usar:** Operando a loja, vendas reais, dados reais
- **Banco de dados:** PostgreSQL (Docker, persistente)
- **Docker:** SIM (obrigatório)
- **Iniciar:** `INICIAR_PRODUCAO.bat`
- **Dados:** REAIS (com backup automático)
- **⚠️ CUIDADO:** Não apague dados aqui!

---

## 🚀 Como Usar

### Primeira vez - DESENVOLVIMENTO
```bash
# 1. Copie o exemplo
copy .env.example .env.development

# 2. Inicie o sistema
INICIAR_DEV.bat

# 3. Acesse
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
# Docs:     http://localhost:8000/docs
```

### Primeira vez - PRODUÇÃO
```bash
# 1. Configure as senhas e APIs
notepad .env.production

# 2. Mude pelo menos:
# - POSTGRES_PASSWORD (senha forte!)
# - JWT_SECRET_KEY (gere com: python -c "import secrets; print(secrets.token_urlsafe(64))")
# - ADMIN_TOKEN (algo único)

# 3. Inicie Docker Desktop

# 4. Inicie o sistema
INICIAR_PRODUCAO.bat

# 5. Aguarde ~30 segundos

# 6. Acesse
# Backend: http://localhost:8000
# Docs:    http://localhost:8000/docs
```

---

## 📂 Estrutura de Arquivos

```
Sistema Pet/
├── .env.development        ← Desenvolvimento (SQLite)
├── .env.production         ← Produção (PostgreSQL + Docker)
│
├── docker-compose.production.yml  ← USAR ESTE
│
├── INICIAR_DEV.bat         ← Desenvolvimento
├── INICIAR_PRODUCAO.bat    ← Produção
│
├── backend/
│   ├── data/
│   │   └── petshop_dev.db  ← Banco SQLite (dev)
│   └── ...
│
├── backups/                ← Backups automáticos (produção)
│   ├── backup_20260203_080000.dump
│   ├── backup_20260203_140000.dump
│   └── ...
│
└── frontend/
    └── ...
```

---

## ⚙️ Comandos Úteis

### DESENVOLVIMENTO
```bash
# Iniciar
INICIAR_DEV.bat

# Parar: Feche as janelas do terminal

# Resetar banco (apagar dados de teste)
del backend\data\petshop_dev.db
```

### PRODUÇÃO
```bash
# Iniciar
INICIAR_PRODUCAO.bat

# Ver logs
docker-compose -f docker-compose.production.yml logs -f

# Ver status
docker-compose -f docker-compose.production.yml ps

# Parar
docker-compose -f docker-compose.production.yml down

# Backup manual
docker exec petshop-prod-postgres pg_dump -U petshop_prod -d petshop_production_db -F c -f /backups/backup_manual.dump

# Restaurar backup
docker exec -i petshop-prod-postgres pg_restore -U petshop_prod -d petshop_production_db -c /backups/backup_YYYYMMDD_HHMMSS.dump
```

---

## 🔐 Checklist de Segurança (PRODUÇÃO)

Antes de usar PRODUÇÃO, verifique:

- [ ] `POSTGRES_PASSWORD` alterada (mínimo 20 caracteres, forte)
- [ ] `JWT_SECRET_KEY` gerado novo (64 caracteres aleatórios)
- [ ] `ADMIN_TOKEN` alterado para algo único
- [ ] `STONE_SANDBOX=false` se for usar pagamentos reais
- [ ] APIs configuradas com suas chaves reais
- [ ] Docker Desktop instalado e rodando
- [ ] Pasta `backups/` existe
- [ ] Testado backup e restore

---

## ❓ FAQ

### Qual a diferença entre os ambientes?
- **DEV:** Rápido, sem Docker, SQLite, dados de teste
- **PROD:** Completo, com Docker, PostgreSQL, dados reais, backups

### Posso usar os dois ao mesmo tempo?
Não! Os dois usam as mesmas portas (8000, 5173). Use um de cada vez.

### Quando devo usar cada um?
- **DEV:** Sempre que estiver programando/testando
- **PROD:** Apenas quando for operar a loja com clientes reais

### E se eu quebrar algo em DEV?
Sem problemas! É só apagar o banco SQLite e criar novo.

### E se eu quebrar algo em PROD?
Por isso temos backups automáticos a cada 6h! Use o restore.

### Preciso do Docker para desenvolvimento?
NÃO! Use `INICIAR_DEV.bat` que roda tudo localmente.

### Preciso do Docker para produção?
SIM! É obrigatório. Baixe em: https://www.docker.com/products/docker-desktop

---

## 🆘 Problemas Comuns

### "Docker não está rodando"
1. Abra Docker Desktop
2. Aguarde iniciar completamente
3. Rode novamente `INICIAR_PRODUCAO.bat`

### "Erro de autenticação PostgreSQL"
1. Verifique o arquivo `.env.production`
2. Senha do banco está correta?
3. Tente parar e iniciar novamente:
```bash
docker-compose -f docker-compose.production.yml down
INICIAR_PRODUCAO.bat
```

### "Porta 8000 já está em uso"
Você tem outro ambiente rodando! Pare-o primeiro:
```bash
# Se for dev: feche as janelas
# Se for prod:
docker-compose -f docker-compose.production.yml down
```

### "Backend não responde"
1. Aguarde 30 segundos após iniciar
2. Verifique logs:
```bash
docker-compose -f docker-compose.production.yml logs backend
```

---

**Última atualização:** 03/02/2026
