# 🔍 DIAGNÓSTICO DOS AMBIENTES - Sistema Pet Shop

**Data:** 12/02/2026
**Status:** REQUER ORGANIZAÇÃO

---

## 📊 SITUAÇÃO ATUAL (O QUE ESTÁ RODANDO)

```
┌─────────────────────────────────────────────────────────────┐
│ CONTAINER               PORTA        STATUS                 │
├─────────────────────────────────────────────────────────────┤
│ petshop-dev-postgres    5433 → 5432  ✅ Healthy (2 horas)   │
│ petshop-dev-backend     8000 → 8000  ✅ Healthy (46 min)    │
│ petshop-prod-postgres   5434 → 5432  ✅ Healthy (6 min)     │
│ petshop-prod-backend    8001 → 8000  ❌ NÃO ESTÁ RODANDO    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ ARQUIVOS DOCKER-COMPOSE EXISTENTES

### 1️⃣ `docker-compose.development.yml` (DEV - TESTES)
**Para que serve:** Desenvolvimento/testes locais
```yaml
Postgres: porta 5433
  - Container: petshop-dev-postgres
  - User: postgres / postgres
  - Database: petshop_dev
  - ✅ RODANDO

Backend: porta 8000
  - Container: petshop-dev-backend
  - ✅ RODANDO
```

### 2️⃣ `docker-compose.production-local.yml` (PILOTO NA LOJA)
**Para que serve:** Rodar piloto na loja com dados reais
```yaml
Postgres: porta 5434
  - Container: petshop-prod-postgres
  - User: petshop_user / petshop_pass_2026
  - Database: petshop_prod
  - ✅ RODANDO
  - ❌ PROBLEMA: Banco VAZIO (sem tabelas!)

Backend: porta 8001
  - Container: petshop-prod-backend
  - ❌ NÃO ESTÁ RODANDO
```

### 3️⃣ `docker-compose.production.yml` (PARA SERVIDOR ONLINE)
**Para que serve:** Rodar na Ocean (mlprohub.com.br)
```yaml
Postgres: porta 5432 ⚠️ CONFLITA COM DEV SE RODAR LOCAL!
  - Container: petshop-prod-postgres
  - ❌ NÃO PODE USAR LOCALMENTE

Backend: porta 8000 ⚠️ CONFLITA COM DEV!
  - Container: petshop-prod-backend
  - ❌ NÃO PODE USAR LOCALMENTE
```

---

## ❌ PROBLEMAS IDENTIFICADOS

### 🔴 CRÍTICO:
1. **Banco PROD_LOCAL vazio** (migrations não aplicadas)
   - Tentamos rodar `alembic upgrade head` mas deu erro
   - Banco está rodando mas SEM TABELAS
   
2. **Backend PROD não sobe**
   - Container não está rodando
   - Porta 8001 livre mas backend não iniciou

3. **docker-compose.production.yml CONFLITA com DEV**
   - Usa mesmas portas (5432, 8000)
   - Se tentar rodar local, vai quebrar o DEV

### 🟡 MÉDIA:
4. **Confusão de nomenclatura**
   - 3 arquivos docker-compose (development, production, production-local)
   - Não está claro qual usar quando

5. **Credenciais diferentes entre ambientes**
   - DEV: postgres/postgres
   - PROD_LOCAL: petshop_user/petshop_pass_2026
   - PROD_CLOUD: usa variáveis de ambiente

---

## ✅ SOLUÇÃO PROPOSTA

### ETAPA 1: ORGANIZAR NOMENCLATURA

Renomear arquivos para ficar CRISTALINO:

```
📁 docker-compose.local-dev.yml
   └─ DEV: Testes locais (porta 5433 + 8000)

📁 docker-compose.local-piloto.yml  
   └─ PILOTO: Loja real local (porta 5434 + 8001)

📁 docker-compose.cloud.yml
   └─ CLOUD: Servidor Ocean (porta 5432 + 8000)
```

### ETAPA 2: CORRIGIR BANCO PROD_LOCAL

1. O banco está rodando mas VAZIO
2. Precisamos rodar migrations com credenciais corretas:
   ```bash
   DATABASE_URL=postgresql://petshop_user:petshop_pass_2026@localhost:5434/petshop_prod
   alembic upgrade head
   ```

### ETAPA 3: SUBIR BACKEND PROD_LOCAL

Depois das migrations, subir o backend:
```bash
docker-compose -f docker-compose.local-piloto.yml up -d backend-prod
```

### ETAPA 4: PREPARAR CLOUD (Ocean/mlprohub.com.br)

- Configurar docker-compose.cloud.yml para servidor
- Criar .env separado para produção
- Documentar deploy

---

## 🎯 PLANO DE AÇÃO IMEDIATO

```
☐ 1. Parar tudo que está rodando
☐ 2. Renomear arquivos docker-compose
☐ 3. Ajustar credenciais e portas
☐ 4. Subir DEV novamente (limpo)
☐ 5. Aplicar migrations no PROD_LOCAL
☐ 6. Subir PROD_LOCAL completo
☐ 7. Testar os 2 ambientes juntos
☐ 8. Criar documentação clara
☐ 9. Preparar CLOUD posteriormente
```

---

## 🤔 PERGUNTAS PARA VOCÊ

1. **Quer que eu organize TUDO agora?** (renomear, corrigir, documentar)
   
2. **DEV atual pode parar?** (vou reorganizar mas não perde dados)

3. **Sobre o CLOUD (mlprohub.com.br):**
   - Quer tirar o que está lá e subir este sistema?
   - Precisa ser AGORA ou podemos focar primeiro no PILOTO local?

---

## 💡 RECOMENDAÇÃO

**Vamos fazer na ordem:**

1. ✅ **HOJE:** Organizar DEV + PILOTO_LOCAL (máquina)
2. ✅ **PRÓXIMO:** Preparar CLOUD para Ocean/mlprohub.com.br
3. ✅ **DEPOIS:** Implementar sincronização local ↔ cloud

**Sobre sua dúvida:** *"Queria ter o online e instalado local na máquina pra se cair o online o local segue tocando"*

✅ **SIM, É POSSÍVEL!** Existem 3 estratégias:
- **Redundância:** Sistema rodando local + cloud simultaneamente
- **Sincronização:** Backups automáticos cloud → local
- **Failover:** Se cloud cai, redireciona para local (requer DNS dinâmico)

Vou detalhar isso após organizar os ambientes!

---

**Aguardando sua aprovação para:**
- [ ] Reorganizar TUDO agora
- [ ] Focar só no PILOTO local primeiro
- [ ] Explicar estratégia cloud + local failover

📌 **O que você prefere?**
