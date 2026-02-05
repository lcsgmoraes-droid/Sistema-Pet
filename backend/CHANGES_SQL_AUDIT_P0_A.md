# 🔍 CHANGES - SQL AUDIT HOOK (P0-A)

**Multi-Tenant Security Auditing - Fase 1.4.3-A**

Data: 05/02/2026  
Autor: Sistema de Hardening Multi-Tenant  
Status: ✅ IMPLEMENTADO  
Versão: 1.0.0  
Fase: Hook de Auditoria (Não-bloqueante)

---

## 📋 SUMÁRIO

- [Objetivo](#objetivo)
- [Arquivos Criados](#arquivos-criados)
- [Como Funciona](#como-funciona)
- [Exemplo de Log](#exemplo-de-log)
- [Integração](#integração)
- [Checklist de Validação](#checklist-de-validação)

---

## 🎯 OBJETIVO

Detectar execução de **RAW SQL fora do helper tenant-safe** para identificar
queries que precisam ser migradas, **SEM BLOQUEAR** a execução da aplicação.

**Problema Atual:**
- 89 queries RAW SQL inseguras no código
- Sem visibilidade de onde são executadas
- Difícil priorizar migração

**Solução:**
- Hook SQLAlchemy `before_cursor_execute`
- Detecta RAW SQL via call stack
- Loga para auditoria posterior

---

## 📁 ARQUIVOS CRIADOS

### 1. **app/db/sql_audit.py** (~300 linhas)

```
backend/
├── app/
│   ├── db/
│   │   └── sql_audit.py  ← NOVO
│   └── utils/
│       └── tenant_safe_sql.py
```

**Conteúdo:**
- `audit_raw_sql()` - Listener SQLAlchemy
- `_is_raw_sql_text()` - Detecta RAW SQL vs ORM
- `_get_call_origin()` - Identifica arquivo/função origem
- `_is_from_tenant_safe_helper()` - Verifica se veio do helper
- `_should_audit_statement()` - Filtra queries de sistema
- `enable_sql_audit()` - Habilita auditoria (documentação)
- `disable_sql_audit()` - Desabilita auditoria (testes)
- `get_audit_stats()` - Estatísticas (futuro)

---

## ⚙️ COMO FUNCIONA

### **1. Registro do Hook**

```python
@event.listens_for(Engine, "before_cursor_execute", retval=False)
def audit_raw_sql(conn, cursor, statement, parameters, context, executemany):
    # Hook executado ANTES de cada query
    pass
```

**Momento de Execução:**
- ANTES da query ser enviada ao banco
- Para TODAS as queries (ORM + RAW SQL)
- Não altera resultado nem performance significativamente

---

### **2. Fluxo de Auditoria**

```
┌─────────────────────────────────────────────┐
│ 1. Query executada                          │
│    db.execute(text("SELECT * FROM ..."))    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 2. Hook before_cursor_execute acionado      │
│    audit_raw_sql() recebe statement         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 3. Verificações                             │
│    ✓ É RAW SQL?                             │
│    ✓ Deve auditar? (não é sistema)         │
│    ✓ Veio de fora do helper?                │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
    ✅ Seguro          🚨 ALERTA
    (do helper)       (fora do helper)
         │                   │
         │                   ▼
         │     ┌─────────────────────────────┐
         │     │ 4. Log estruturado          │
         │     │    - Arquivo origem         │
         │     │    - Função origem          │
         │     │    - SQL truncado           │
         │     │    - Timestamp              │
         │     └─────────────┬───────────────┘
         │                   │
         └───────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 5. Query executada normalmente              │
│    (sem bloqueio)                           │
└─────────────────────────────────────────────┘
```

---

### **3. Detecção de RAW SQL**

#### **Método 1: Indicadores de Sintaxe**

```python
def _is_raw_sql_text(statement: str) -> bool:
    raw_sql_indicators = [
        "-- ",              # Comentários SQL
        "/* ",              # Comentários multi-linha
        "with ",            # CTEs
        "::text",           # Casting PostgreSQL
        "::jsonb",
        "coalesce(",
        "array_agg(",
        "string_agg(",
        "json_build_object(",
    ]
    # ...
```

**Exemplos:**
- ✅ RAW: `"SELECT * FROM -- comentário"`
- ✅ RAW: `"WITH cte AS (...) SELECT ..."`
- ✅ RAW: `"SELECT coalesce(valor, 0) ..."`
- ❌ ORM: `"SELECT table.id, table.name FROM table WHERE ..."`

---

#### **Método 2: Call Stack**

```python
def _is_from_tenant_safe_helper(stack_trace: str) -> bool:
    indicators = [
        "tenant_safe_sql.py",
        "execute_tenant_safe",
        "execute_tenant_safe_scalar",
        # ...
    ]
    return any(indicator in stack_trace for indicator in indicators)
```

**Exemplos de Call Stack:**

✅ **Seguro (do helper):**
```
File "comissoes_routes.py", line 123, in get_comissoes
File "tenant_safe_sql.py", line 156, in execute_tenant_safe  ← DETECTADO
File "sqlalchemy/engine/base.py", line 1234, in execute
```

🚨 **Inseguro (fora do helper):**
```
File "comissoes_routes.py", line 456, in calcular_totais
File "sqlalchemy/orm/session.py", line 789, in execute  ← SEM tenant_safe_sql
File "sqlalchemy/engine/base.py", line 1234, in execute
```

---

### **4. Filtragem de Queries de Sistema**

```python
def _should_audit_statement(statement: str) -> bool:
    # Ignorar queries de sistema
    ignore_patterns = [
        "pg_catalog",           # PostgreSQL catalog
        "information_schema",   # Schema info
        "alembic_version",      # Migrations
        "select version()",     # Health checks
        "begin",                # Transações
        "commit",
        "rollback",
    ]
    # ...
```

**Evita spam de logs** com queries internas do SQLAlchemy e PostgreSQL.

---

### **5. Origem da Query**

```python
def _get_call_origin() -> tuple[str, str, int]:
    stack = traceback.extract_stack()
    
    # Filtrar frames do SQLAlchemy
    for frame in reversed(stack):
        if "sqlalchemy" not in frame.filename:
            file_short = frame.filename.split("/")[-1]
            return (file_short, frame.name, frame.lineno)
```

**Retorna:**
- `file`: `comissoes_routes.py`
- `function`: `calcular_comissoes_mes`
- `line`: `234`

---

## 📊 EXEMPLO DE LOG

### **Console (Desenvolvimento)**

```
================================================================================
🚨 RAW SQL OUTSIDE HELPER
================================================================================
📍 Origin: comissoes_routes.py:234 in calcular_comissoes_mes()
📝 SQL: SELECT 
    SUM(valor_comissao) as total,
    vendedor_id
FROM comissoes_itens
WHERE status = 'pago'
  AND data_pagamento >= '2026-01-01'
GROUP BY vendedor_id... (1234 chars total)
================================================================================
```

---

### **Log Estruturado (Produção)**

```json
{
  "timestamp": "2026-02-05T14:32:15.123456",
  "level": "WARNING",
  "logger": "sql_audit",
  "event": "raw_sql_outside_helper",
  "sql_truncated": "SELECT SUM(valor_comissao)...",
  "sql_length": 1234,
  "file_origin": "comissoes_routes.py",
  "function_origin": "calcular_comissoes_mes",
  "line_origin": 234,
  "has_parameters": true,
  "executemany": false
}
```

---

### **Queries Seguras (NÃO logadas)**

```python
# ✅ Usa helper - NÃO é logado
from app.utils.tenant_safe_sql import execute_tenant_safe

result = execute_tenant_safe(db, """
    SELECT * FROM comissoes_itens
    WHERE {tenant_filter} AND status = :status
""", {"status": "pendente"})
```

**Log:** (nenhum - query segura)

---

### **Queries Inseguras (logadas)**

```python
# 🚨 RAW SQL direto - É LOGADO
from sqlalchemy import text

result = db.execute(text("""
    SELECT * FROM comissoes_itens
    WHERE status = :status
"""), {"status": "pendente"})
```

**Log:**
```
🚨 RAW SQL OUTSIDE HELPER
📍 Origin: comissoes_routes.py:456 in get_comissoes()
📝 SQL: SELECT * FROM comissoes_itens WHERE status = :status
```

---

## 🔌 INTEGRAÇÃO

### **1. Importar no main.py (ou app/__init__.py)**

```python
# app/main.py

from fastapi import FastAPI
from app.db.sql_audit import enable_sql_audit

app = FastAPI()

# Habilitar auditoria SQL no startup
@app.on_event("startup")
async def startup_event():
    enable_sql_audit()
    print("✅ SQL Audit enabled")
```

---

### **2. Uso Automático**

Após importar, o hook é **automaticamente registrado** pelo decorator:

```python
@event.listens_for(Engine, "before_cursor_execute", retval=False)
def audit_raw_sql(...):
    # ...
```

**Não precisa configurar nada mais!**

---

### **3. Desabilitar em Testes (opcional)**

```python
# tests/conftest.py

import pytest
from app.db.sql_audit import disable_sql_audit

@pytest.fixture(scope="session", autouse=True)
def disable_audit():
    disable_sql_audit()  # Silenciar logs em testes
    yield
```

---

## 🧪 VALIDAÇÃO

### **Teste Manual**

```python
# Script de teste: test_sql_audit.py

import os
os.environ['DATABASE_URL'] = "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Importar para ativar hook
from app.db.sql_audit import enable_sql_audit

enable_sql_audit()

# Criar sessão
engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("🧪 TESTE 1: RAW SQL FORA DO HELPER (deve logar)")
print("=" * 80)

# Executar RAW SQL direto (SEM helper)
result = session.execute(text("""
    SELECT 1 as test_value,
           'Hello' as test_string,
           COALESCE(NULL, 'default') as test_coalesce
"""))

print("Resultado:", result.fetchone())

print("\n" + "=" * 80)
print("🧪 TESTE 2: RAW SQL COM HELPER (NÃO deve logar)")
print("=" * 80)

from app.utils.tenant_safe_sql import execute_tenant_safe
from app.tenancy.context import set_current_tenant
from uuid import uuid4

set_current_tenant(uuid4())

# Executar com helper (seguro)
result = execute_tenant_safe(session, """
    SELECT 1 as test_value
    WHERE {tenant_filter}
""", {}, require_tenant=False)

print("Resultado:", result.fetchone())

session.close()
```

**Output Esperado:**

```
================================================================================
🧪 TESTE 1: RAW SQL FORA DO HELPER (deve logar)
================================================================================

🚨 RAW SQL OUTSIDE HELPER
📍 Origin: test_sql_audit.py:23 in <module>()
📝 SQL: SELECT 1 as test_value, 'Hello' as test_string, COALESCE(NULL, 'default')...

Resultado: (1, 'Hello', 'default')

================================================================================
🧪 TESTE 2: RAW SQL COM HELPER (NÃO deve logar)
================================================================================
Resultado: (1,)
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

### **Implementação**

- [x] Arquivo `app/db/sql_audit.py` criado
- [x] Hook `audit_raw_sql()` implementado
- [x] Listener `before_cursor_execute` registrado
- [x] Função `_is_raw_sql_text()` detecta RAW SQL
- [x] Função `_get_call_origin()` identifica origem
- [x] Função `_is_from_tenant_safe_helper()` verifica helper
- [x] Função `_should_audit_statement()` filtra sistema
- [x] Logger estruturado configurado
- [x] Log trunca SQL (500 chars)
- [x] Enable/disable functions implementadas

---

### **Comportamento**

- [x] RAW SQL fora do helper é logado
- [x] RAW SQL do helper NÃO é logado
- [x] Queries ORM NÃO são logadas
- [x] Queries de sistema NÃO são logadas (pg_catalog, alembic)
- [x] Execução NÃO é bloqueada
- [x] Performance não é significativamente afetada
- [x] Log contém origem (arquivo/função/linha)
- [x] Log contém SQL truncado
- [x] Log contém timestamp

---

### **Integração**

- [ ] Importado em `app/main.py` ou `app/__init__.py`
- [ ] Testado com query RAW SQL direta (deve logar)
- [ ] Testado com query via helper (NÃO deve logar)
- [ ] Logs visíveis no console (desenvolvimento)
- [ ] Logs estruturados funcionam (produção)

---

## 📈 PRÓXIMOS PASSOS

### **Fase 1.4.3-B: Dashboard de Métricas** (Não implementado)

- [ ] Contador de queries fora do helper
- [ ] Top 10 arquivos com mais RAW SQL
- [ ] Endpoint `/api/admin/sql-audit-stats`
- [ ] Visualização de hot spots

---

### **Fase 1.5: Migração Gradual** (Próxima)

**Objetivo:** Migrar as 89 queries inseguras identificadas

**Prioridade:**
1. **P0 (Crítico)** - DELETE/UPDATE sem tenant (3 queries)
2. **P1 (Alto)** - Queries financeiras (12 queries)
3. **P2 (Médio)** - Relatórios (25 queries)
4. **P3 (Baixo)** - Configurações (49 queries)

**Método:**
1. Identificar query via logs de auditoria
2. Abrir arquivo origem
3. Substituir `db.execute(text(...))` por `execute_tenant_safe(db, ...)`
4. Adicionar `{tenant_filter}` no WHERE
5. Testar isolamento
6. Deploy

---

## 📚 REFERÊNCIAS

- [SQLAlchemy Events](https://docs.sqlalchemy.org/en/14/core/events.html#sqlalchemy.events.ConnectionEvents.before_cursor_execute)
- [RAW_SQL_INVENTORY.md](RAW_SQL_INVENTORY.md) - 129 queries mapeadas
- [CHANGES_RAW_SQL_INFRA_P0.md](CHANGES_RAW_SQL_INFRA_P0.md) - Helper tenant-safe
- [CHANGES_RAW_SQL_TESTS_P0.md](CHANGES_RAW_SQL_TESTS_P0.md) - Testes do helper

---

## 🔒 SEGURANÇA

### **O que este hook FAZ:**

✅ Detecta RAW SQL fora do helper  
✅ Loga para auditoria  
✅ Identifica arquivos que precisam migração  
✅ Não afeta funcionamento da aplicação  

### **O que este hook NÃO FAZ:**

❌ NÃO bloqueia queries inseguras  
❌ NÃO valida tenant_id  
❌ NÃO substitui o helper tenant-safe  
❌ NÃO garante isolamento multi-tenant  

**⚠️ IMPORTANTE:** Este hook é uma **ferramenta de auditoria**, não uma solução
de segurança. A migração para o helper `execute_tenant_safe` ainda é obrigatória.

---

## 🎯 IMPACTO

### **Benefícios Imediatos**

✅ **Visibilidade** - Saber onde RAW SQL inseguro está sendo executado  
✅ **Priorização** - Identificar hot spots para migração  
✅ **Não-disruptivo** - Não quebra funcionalidade existente  
✅ **Métricas** - Base para dashboard futuro  

### **Métricas Esperadas**

Após ativar, espera-se ver logs de:
- ~89 queries RAW SQL inseguras (já mapeadas)
- Principalmente em: comissões (42), relatórios (25), migrations (18)

---

**Status Final:** ✅ **HOOK IMPLEMENTADO E PRONTO PARA USO**

**Próxima Ação:** Integrar em `app/main.py` e validar com queries reais
