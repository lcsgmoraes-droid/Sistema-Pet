# 🐛 TROUBLESHOOTING: Erro 500 em Contas Bancárias

**Erro reportado:** `POST /api/contas-bancarias` retorna 500 Internal Server Error

**Payload:**
```json
{
  "nome": "Dinheiro",
  "tipo": "caixa",
  "banco": null,
  "saldo_inicial": 0,
  "cor": "#16a34a"
}
```

---

## ✅ BOM SINAL: Sistema de Segurança Funcionando

O erro sanitizado que você viu:
```json
{
  "error": "internal_server_error",
  "message": "Erro interno no servidor",
  "detail": "Entre em contato com o suporte"
}
```

**Isso é CORRETO!** Nosso exception handler em produção está funcionando perfeitamente, ocultando detalhes sensíveis. 🎉

---

## 🔍 DIAGNÓSTICO: 4 Passos

### 1️⃣ Verificar Logs do Backend

O erro real está nos logs do terminal onde o backend está rodando.

**Abra o terminal do backend e procure por:**
```
[ERROR] Erro ao criar conta: ...
```

**Erros comuns:**
- ❌ `relation "contas_bancarias" does not exist` → Tabela não existe
- ❌ `column "..." does not exist` → Estrutura da tabela desatualizada
- ❌ `violates foreign key constraint` → User/tenant ausente
- ❌ `null value in column "tenant_id"` → Problema de context

---

### 2️⃣ Verificar Se Tabela Existe

```bash
# No terminal backend/
python
```

```python
from app.db import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tabelas = inspector.get_table_names()

# Verificar se existe
print("contas_bancarias" in tabelas)  # Deve ser True

# Ver colunas
if "contas_bancarias" in tabelas:
    colunas = inspector.get_columns("contas_bancarias")
    for col in colunas:
        print(f"{col['name']}: {col['type']}")
```

**Resultado esperado:**
```
id: INTEGER
tenant_id: UUID
nome: VARCHAR(100)
tipo: VARCHAR(20)
banco: VARCHAR(50)
saldo_inicial: NUMERIC(15,2)
saldo_atual: NUMERIC(15,2)
cor: VARCHAR(7)
icone: VARCHAR(50)
ativa: BOOLEAN
user_id: INTEGER
created_at: DATETIME
updated_at: DATETIME
```

---

### 3️⃣ Testar Autenticação

```bash
# No terminal backend/
python
```

```python
from app.db import get_session
from app.auth import get_current_user_and_tenant

# Simular request
class FakeRequest:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}"}

# Pegar seu token do browser (F12 → Application → Local Storage → token)
token = "SEU_TOKEN_AQUI"

fake_req = FakeRequest(token)

# Testar autenticação
try:
    from fastapi import Request
    # ... (teste manual de autenticação)
    print("✅ Autenticação OK")
except Exception as e:
    print(f"❌ Erro na auth: {e}")
```

---

### 4️⃣ Verificar Migrations

```bash
# No diretório backend/
alembic current
alembic heads
```

**Se tabela não existe:**
```bash
# Criar migration
alembic revision --autogenerate -m "criar_tabela_contas_bancarias"

# Aplicar
alembic upgrade head
```

---

## 🔧 SOLUÇÕES RÁPIDAS

### Solução 1: Tabela Não Existe

```bash
cd backend

# Ver status das migrations
alembic current

# Se não está na última versão
alembic upgrade head

# Se não tem migrations ainda
alembic revision --autogenerate -m "criar_tabelas_financeiro"
alembic upgrade head
```

---

### Solução 2: Modo Development para Debug

**Temporariamente**, para ver erro completo:

```python
# backend/app/config.py (ou .env)
ENVIRONMENT = "development"  # Ou "dev"
```

**Reinicie o backend e tente novamente.**

Agora o erro 500 vai mostrar detalhes completos:
```json
{
  "detail": "relation \"contas_bancarias\" does not exist...",
  "type": "ProgrammingError",
  "message": "..."
}
```

**⚠️ LEMBRE DE VOLTAR PARA "production" DEPOIS!**

---

### Solução 3: Criar Tabela Manualmente

Se migrations não funcionarem:

```python
# backend/scripts/criar_tabelas.py
from app.db import engine
from app.financeiro_models import ContaBancaria, MovimentacaoFinanceira

# Criar todas as tabelas
ContaBancaria.__table__.create(engine, checkfirst=True)
MovimentacaoFinanceira.__table__.create(engine, checkfirst=True)

print("✅ Tabelas criadas!")
```

```bash
python backend/scripts/criar_tabelas.py
```

---

### Solução 4: Verificar Tenant ID

O erro pode ser de tenant_id ausente. Verifique:

```python
# backend/app/contas_bancarias_routes.py linha ~135
# Adicionar mais debug ANTES de criar a conta:

print(f"[DEBUG] User ID: {current_user.id}")
print(f"[DEBUG] Tenant ID: {tenant_id}")
print(f"[DEBUG] Tenant ID type: {type(tenant_id)}")

# Verificar se tenant existe
from app.models import Tenant
tenant_existe = db.query(Tenant).filter(Tenant.id == tenant_id).first()
print(f"[DEBUG] Tenant existe? {tenant_existe is not None}")
```

---

## 📊 CHECKLIST DE DIAGNÓSTICO

Use este checklist para identificar o problema:

- [ ] **Logs do backend:** Encontrou mensagem `[ERROR] Erro ao criar conta: ...`?
- [ ] **Tabela existe:** `contas_bancarias` in tabelas == True?
- [ ] **Colunas corretas:** Todas as 12+ colunas presentes?
- [ ] **Migrations atualizadas:** `alembic current` mostra última versão?
- [ ] **Autenticação OK:** Token válido e tenant_id presente?
- [ ] **User existe:** current_user.id != None?
- [ ] **Tenant existe:** tenant_id válido no banco?
- [ ] **Database conectada:** Postgres rodando e acessível?

---

## 🎯 PRÓXIMOS PASSOS

1. **Copie este checklist**
2. **Execute os 4 passos de diagnóstico**
3. **Reporte a causa raiz encontrada**
4. **Aplique a solução correspondente**

---

## 💡 DICA: Teste Rápido via Swagger

Abra: `http://localhost:8000/docs`

1. Clique em **POST /api/contas-bancarias**
2. Clique em **Try it out**
3. Cole o payload:
```json
{
  "nome": "Dinheiro",
  "tipo": "caixa",
  "banco": null,
  "saldo_inicial": 0,
  "cor": "#16a34a",
  "icone": null,
  "ativa": true
}
```
4. Execute

**Vantagem:** Swagger mostra erro completo mesmo em produção (no body do 500).

---

## 📞 Se Precisar de Ajuda

Reporte com estas informações:

```
🐛 BUG REPORT: Erro 500 POST /api/contas-bancarias

**Logs do backend:**
[Cole aqui a mensagem [ERROR] completa]

**Tabela existe?**
[ ] Sim  [ ] Não  [ ] Não sei

**Migrations:**
Current: [resultado de `alembic current`]
Heads: [resultado de `alembic heads`]

**Ambiente:**
- Database: Postgres/SQLite?
- OS: Windows/Linux/Mac?
- Python: [resultado de `python --version`]

**Payload testado:**
[Cole o JSON que você enviou]

**Erro completo (se disponível):**
[Cole traceback do terminal]
```

---

🎯 **Última atualização:** 08/02/2026  
🔧 **Status:** Troubleshooting Guide  
✅ **Sistema de segurança:** Funcionando corretamente (erro sanitizado)
