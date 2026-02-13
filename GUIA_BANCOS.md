# 📚 GUIA DOS BANCOS DE DADOS

Este guia explica como funcionam os 2 bancos de dados do sistema.

---

## 🔵 BANCO DEV (Desenvolvimento/Testes)

**Para que serve:** Continuar testando e desenvolvendo funcionalidades

### Informações:
- **Nome do container:** `petshop-dev-postgres`
- **Nome do banco:** `petshop_dev`
- **Porta:** `5432`
- **Backend:** `http://localhost:8000`
- **Dados:** Vendas de teste, produtos fictícios, clientes de exemplo

### Como usar:

```bash
# Subir ambiente DEV (o que você já usa)
docker-compose -f docker-compose.development.yml up -d

# Ver logs
docker-compose -f docker-compose.development.yml logs -f

# Parar
docker-compose -f docker-compose.development.yml down
```

### Quando usar:
✅ Testar novas funcionalidades  
✅ Desenvolver código  
✅ Fazer experimentos  
✅ Gerar relatórios de teste  
❌ NÃO usar para vendas reais da loja!

---

## 🟢 BANCO PROD_LOCAL (Produção Local / Piloto)

**Para que serve:** Rodar o piloto na loja com dados REAIS

### Informações:
- **Nome do container:** `petshop-prod-postgres`
- **Nome do banco:** `petshop_prod`
- **Porta:** `5433` (diferente!)
- **Backend:** `http://localhost:8001` (porta diferente!)
- **Dados:** Banco LIMPO, só com configurações essenciais

### Setup inicial (FAÇA UMA VEZ):

```bash
# 1. Subir o banco de produção
docker-compose -f docker-compose.production-local.yml up -d postgres-prod

# 2. Aguardar 30 segundos

# 3. Criar banco limpo com configurações
python backend/criar_banco_producao.py

# 4. Subir o backend de produção
docker-compose -f docker-compose.production-local.yml up -d backend-prod
```

### Login inicial:
- **Email:** `admin@petshop.com`
- **Senha:** `admin123`
- 🔴 **IMPORTANTE:** Altere a senha após o primeiro login!

### Como usar no dia a dia:

```bash
# Subir ambiente PROD_LOCAL
docker-compose -f docker-compose.production-local.yml up -d

# Ver logs
docker-compose -f docker-compose.production-local.yml logs -f

# Parar (fim do dia)
docker-compose -f docker-compose.production-local.yml down
```

### Quando usar:
✅ Vendas reais da loja  
✅ Cadastrar produtos reais  
✅ Clientes reais  
✅ Gerar NF-es reais  
❌ NÃO testar funcionalidades novas aqui!

---

## 🎯 RODANDO OS 2 AO MESMO TEMPO

Você pode rodar DEV e PROD_LOCAL **simultaneamente** (portas diferentes):

```bash
# Subir DEV (testes)
docker-compose -f docker-compose.development.yml up -d

# Subir PROD_LOCAL (piloto)
docker-compose -f docker-compose.production-local.yml up -d
```

**Resultado:**
- DEV: `http://localhost:8000` (backend) + porta 5432 (postgres)
- PROD: `http://localhost:8001` (backend) + porta 5433 (postgres)

---

## 📊 COMPARAÇÃO RÁPIDA

| Característica | DEV 🔵 | PROD_LOCAL 🟢 |
|---|---|---|
| **Porta Backend** | 8000 | 8001 |
| **Porta Postgres** | 5432 | 5433 |
| **Dados** | Teste/Fictícios | Reais da loja |
| **Usuário admin** | admin@test.com | admin@petshop.com |
| **Quando usar** | Desenvolver/Testar | Rodar piloto na loja |
| **Pode perder dados?** | ✅ Sim (é teste) | ❌ NÃO (dados reais) |

---

## 🔐 SEGURANÇA PROD_LOCAL

Antes de usar em produção:

1. **Gerar nova JWT_SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
   Copiar resultado para `.env.production-local`

2. **Alterar senha do admin** após primeiro login

3. **Fazer backups regulares:**
```bash
# Backup do banco PROD
docker exec petshop-prod-postgres pg_dump -U petshop_user petshop_prod > backup_prod_$(date +%Y%m%d_%H%M%S).sql
```

---

## 🆘 SOLUÇÃO DE PROBLEMAS

### Backend não conecta no banco:
```bash
# Verificar se o banco está rodando
docker ps | grep petshop

# Ver logs do banco
docker logs petshop-prod-postgres
```

### Erro de porta já em uso:
```bash
# Verificar o que está usando a porta
netstat -ano | findstr :5433

# Para portas diferentes, editar docker-compose.production-local.yml
```

### Resetar banco de produção (CUIDADO!):
```bash
# Para tudo
docker-compose -f docker-compose.production-local.yml down -v

# Subir de novo e recriar
docker-compose -f docker-compose.production-local.yml up -d postgres-prod
python backend/criar_banco_producao.py
```

---

## 📞 DÚVIDAS?

Se tiver dúvidas, pergunte! Mas lembre-se:

- **DEV** 🔵 = Testar/Desenvolver (pode quebrar)
- **PROD_LOCAL** 🟢 = Piloto real (cuidado!)

---

**Última atualização:** 12/02/2026
