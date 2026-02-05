# 🔒 CHANGES - SQL AUDIT ENFORCEMENT (P0-D)

**Multi-Tenant Security Enforcement - Fase 1.4.3-D**

Data: 05/02/2026  
Autor: Sistema de Hardening Multi-Tenant  
Status: ✅ IMPLEMENTADO  
Versão: 1.3.0  
Fase: Enforcement de Queries HIGH Risk

---

## 📋 SUMÁRIO

- [Objetivo](#objetivo)
- [Flags e Configuração](#flags-e-configuração)
- [Comportamento](#comportamento)
- [Casos Bloqueados](#casos-bloqueados)
- [Casos Permitidos](#casos-permitidos)
- [Plano de Rollout](#plano-de-rollout)
- [Checklist de Validação](#checklist-de-validação)

---

## 🎯 OBJETIVO

**Bloquear execução** de queries RAW SQL classificadas como **HIGH risk** quando enforcement estiver ativo.

**Problema:**
- 89 queries HIGH risk identificadas
- Risco de vazamento de dados entre tenants
- Detecção sozinha não impede execução

**Solução:**
- Enforcement opcional via variável de ambiente
- Bloqueia HIGH risk → força uso do helper
- NUNCA bloqueia helper tenant-safe
- Rollout gradual (local → staging → prod)

---

## 🔧 FLAGS E CONFIGURAÇÃO

### Variáveis de Ambiente

#### 1. SQL_AUDIT_ENFORCE

**Tipo:** Boolean  
**Default:** `false`  
**Valores aceitos:** `true`, `false`, `1`, `0`, `yes`, `no`

**Descrição:**
- `false` (default): Apenas loga queries inseguras, **NÃO bloqueia**
- `true`: Bloqueia queries baseado em `SQL_AUDIT_ENFORCE_LEVEL`

**Exemplo:**
```bash
# Desativado (default)
SQL_AUDIT_ENFORCE=false

# Ativado
SQL_AUDIT_ENFORCE=true
```

---

#### 2. SQL_AUDIT_ENFORCE_LEVEL

**Tipo:** Enum  
**Default:** `HIGH`  
**Valores aceitos:** `HIGH`, `MEDIUM`, `LOW`

**Descrição:**
- `HIGH` (default): Bloqueia apenas queries HIGH risk
- `MEDIUM`: Bloqueia MEDIUM e HIGH
- `LOW`: Bloqueia todas as queries RAW SQL fora do helper

**Recomendação:** Use `HIGH` em produção

**Exemplo:**
```bash
# Bloquear apenas HIGH (recomendado)
SQL_AUDIT_ENFORCE_LEVEL=HIGH

# Bloquear MEDIUM+ (mais restritivo)
SQL_AUDIT_ENFORCE_LEVEL=MEDIUM

# Bloquear tudo (desenvolvimento)
SQL_AUDIT_ENFORCE_LEVEL=LOW
```

---

### Configuração no Docker Compose

**docker-compose.yml:**
```yaml
services:
  backend:
    environment:
      # Fase 1: Desenvolvimento (desativado)
      SQL_AUDIT_ENFORCE: "false"
      
      # Fase 2: Staging (apenas HIGH)
      # SQL_AUDIT_ENFORCE: "true"
      # SQL_AUDIT_ENFORCE_LEVEL: "HIGH"
      
      # Fase 3: Produção (apenas HIGH)
      # SQL_AUDIT_ENFORCE: "true"
      # SQL_AUDIT_ENFORCE_LEVEL: "HIGH"
```

---

### Configuração no Código

**Leitura automática ao importar módulo:**
```python
# app/db/sql_audit.py
SQL_AUDIT_ENFORCE = os.getenv("SQL_AUDIT_ENFORCE", "false").lower() in ("true", "1", "yes")
SQL_AUDIT_ENFORCE_LEVEL = os.getenv("SQL_AUDIT_ENFORCE_LEVEL", "HIGH").upper()
```

**Verificar configuração:**
```python
from app.db.sql_audit import get_enforcement_config, is_enforcement_enabled

# Verificar se está ativo
if is_enforcement_enabled():
    print("⚠️  Enforcement ATIVO")

# Ver configuração completa
config = get_enforcement_config()
print(config)
# {
#     "enabled": True,
#     "level": "HIGH",
#     "blocks": "HIGH+ risk queries"
# }
```

---

## ⚙️ COMPORTAMENTO

### Fluxo de Decisão

```
┌─────────────────────────────────────────────┐
│ Query RAW SQL executada                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Veio do helper tenant-safe?                 │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
        SIM                 NÃO
         │                   │
         ▼                   ▼
    ✅ PERMITE      ┌────────────────┐
    (helper é       │ Classificar     │
     sempre OK)     │ risco           │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Enforcement     │
                    │ ativo?          │
                    └────────┬────────┘
                             │
                   ┌─────────┴─────────┐
                   │                   │
                  NÃO                 SIM
                   │                   │
                   ▼                   ▼
              🟢 LOGA          ┌──────────────┐
              (não bloqueia)   │ Risco >=     │
                               │ Threshold?   │
                               └──────┬───────┘
                                      │
                            ┌─────────┴─────────┐
                            │                   │
                           NÃO                 SIM
                            │                   │
                            ▼                   ▼
                       🟢 LOGA            🚫 BLOQUEIA
                       (permite)          RawSQLEnforcementError
```

---

### Lógica de Threshold

```python
# Ordem de severidade
risk_levels_order = ["LOW", "MEDIUM", "HIGH"]

# Exemplo: SQL_AUDIT_ENFORCE_LEVEL=HIGH
enforce_level_index = 2  # HIGH

# Query classificada como MEDIUM
current_risk_index = 1  # MEDIUM

# Comparação
should_block = (current_risk_index >= enforce_level_index)
# should_block = (1 >= 2) = False → NÃO bloqueia
```

**Resultado:**

| Query Risk | Enforce=HIGH | Enforce=MEDIUM | Enforce=LOW |
|-----------|-------------|----------------|-------------|
| LOW       | ✅ Permite   | ✅ Permite      | 🚫 Bloqueia  |
| MEDIUM    | ✅ Permite   | 🚫 Bloqueia     | 🚫 Bloqueia  |
| HIGH      | 🚫 Bloqueia  | 🚫 Bloqueia     | 🚫 Bloqueia  |

---

## 🚫 CASOS BLOQUEADOS

### 1. Query HIGH Risk sem {tenant_filter}

**SQL:**
```sql
SELECT SUM(valor_comissao) FROM comissoes_itens WHERE status = 'pago'
```

**Enforcement:**
```
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=HIGH
```

**Resultado:**
```
RawSQLEnforcementError: 
🚫 RAW SQL BLOCKED: HIGH risk query detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Origin: comissoes_routes.py:234 in calcular_comissoes_mes()
📊 Tables: comissoes_itens
⚠️  Risk: HIGH (enforcement level: HIGH)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Solution:
   Use tenant-safe helper:
   from app.utils.tenant_safe_sql import execute_tenant_safe

   execute_tenant_safe(db, '''
       SELECT * FROM comissoes_itens
       WHERE {tenant_filter} AND ...
   ''', {...})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Docs: See CHANGES_RAW_SQL_INFRA_P0.md
```

---

### 2. UPDATE sem tenant_filter

**SQL:**
```sql
UPDATE vendas SET status = 'cancelada' WHERE id = 123
```

**Problema:** Pode cancelar venda de outro tenant!

**Resultado:**
```
RawSQLEnforcementError: HIGH risk query detected
📍 Origin: vendas_routes.py:456
📊 Tables: vendas
```

---

### 3. DELETE sem tenant_filter

**SQL:**
```sql
DELETE FROM produtos WHERE inativo = true
```

**Problema:** Pode deletar produtos de todos os tenants!

**Resultado:**
```
RawSQLEnforcementError: HIGH risk query detected
📍 Origin: produtos_routes.py:789
📊 Tables: produtos
```

---

## ✅ CASOS PERMITIDOS

### 1. Helper tenant-safe (SEMPRE permitido)

```python
from app.utils.tenant_safe_sql import execute_tenant_safe

# ✅ NUNCA é bloqueado
result = execute_tenant_safe(db, """
    SELECT SUM(valor_comissao) 
    FROM comissoes_itens
    WHERE {tenant_filter}
      AND status = :status
""", {"status": "pago"})
```

**Motivo:** O helper garante isolamento de tenant

---

### 2. Query MEDIUM risk (com Enforce=HIGH)

```python
# Query em tabela whitelist
db.execute(text("SELECT * FROM tenants WHERE id = :id"), {"id": tenant_id})
```

**Classificação:** MEDIUM (tabela whitelist)  
**Enforcement:** HIGH  
**Resultado:** ✅ Permite (MEDIUM < HIGH)

---

### 3. Query LOW risk (com Enforce=HIGH)

```python
# Health check
db.execute(text("SELECT 1"))
```

**Classificação:** LOW (health check)  
**Enforcement:** HIGH  
**Resultado:** ✅ Permite (LOW < HIGH)

---

### 4. Queries de sistema

```python
# Alembic migrations
db.execute(text("SELECT version_num FROM alembic_version"))

# PostgreSQL system queries
db.execute(text("SELECT * FROM pg_catalog.pg_stat_activity"))
```

**Classificação:** LOW (sistema)  
**Resultado:** ✅ Sempre permite

---

### 5. Enforcement desativado

```bash
SQL_AUDIT_ENFORCE=false  # default
```

**Resultado:** ✅ Todas as queries permitidas (apenas loga)

---

## 📅 PLANO DE ROLLOUT

### Fase 0: Preparação (ATUAL)

**Objetivo:** Implementar código, sem ativar

**Ações:**
- ✅ Implementar `RawSQLEnforcementError`
- ✅ Adicionar lógica de bloqueio no hook
- ✅ Criar documentação
- ✅ Criar testes unitários

**Duração:** 1 dia

**Risco:** ZERO (enforcement desativado)

---

### Fase 1: Desenvolvimento Local (1-2 semanas)

**Objetivo:** Testar enforcement com devs

**Configuração:**
```bash
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=HIGH
```

**Ações:**
1. Ativar enforcement em ambiente de dev local
2. Desenvolvedores testam aplicação
3. Identificar queries que quebram
4. Migrar queries HIGH risk → helper
5. Validar que aplicação funciona

**KPI:**
- 0 queries HIGH risk bloqueando funcionalidades críticas
- <5 falsos positivos

**Rollback:**
```bash
SQL_AUDIT_ENFORCE=false
```

**Duração:** 1-2 semanas

**Risco:** BAIXO (apenas dev local)

---

### Fase 2: Staging (1 semana)

**Objetivo:** Validar enforcement em ambiente staging

**Configuração:**
```bash
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=HIGH
```

**Ações:**
1. Ativar enforcement em staging
2. Executar suite de testes completa
3. QA manual de funcionalidades críticas:
   - Vendas
   - Comissões
   - Relatórios
   - Notas fiscais
4. Monitorar logs de bloqueio
5. Corrigir últimas queries HIGH risk

**KPI:**
- 100% de testes passando
- 0 bloqueios em features críticas
- <10 queries HIGH risk restantes

**Rollback:**
```bash
SQL_AUDIT_ENFORCE=false
```

**Duração:** 1 semana

**Risco:** MÉDIO (pode quebrar staging)

---

### Fase 3: Produção Gradual (2-3 semanas)

#### Fase 3.1: Soft Launch (semana 1)

**Objetivo:** Ativar para 10% dos requests

**Configuração:**
```python
# Ativar enforcement para 10% dos requests
import random

if random.random() < 0.10:  # 10%
    os.environ["SQL_AUDIT_ENFORCE"] = "true"
```

**Monitorar:**
- Taxa de erro 500
- Logs de `raw_sql_blocked`
- Feedback de usuários

**KPI:**
- Taxa de erro < 0.1%
- <5 queries HIGH risk bloqueadas por hora

---

#### Fase 3.2: 50% Rollout (semana 2)

**Configuração:**
```python
if random.random() < 0.50:  # 50%
    os.environ["SQL_AUDIT_ENFORCE"] = "true"
```

**KPI:**
- Taxa de erro < 0.1%
- <20 queries HIGH risk bloqueadas por hora

---

#### Fase 3.3: 100% Rollout (semana 3)

**Configuração:**
```bash
SQL_AUDIT_ENFORCE=true
SQL_AUDIT_ENFORCE_LEVEL=HIGH
```

**Permanente no docker-compose.production.yml**

**KPI:**
- Taxa de erro < 0.05%
- 0 queries HIGH risk em produção

**Rollback:**
```bash
SQL_AUDIT_ENFORCE=false
```

**Duração:** 2-3 semanas

**Risco:** ALTO (pode impactar produção)

---

### Fase 4: Hardening (contínuo)

**Objetivo:** Aumentar enforcement gradualmente

**Roadmap:**

1. **Mês 1-2:** Enforce=HIGH (atual)
2. **Mês 3-4:** Enforce=MEDIUM (bloquear também MEDIUM risk)
3. **Mês 5+:** Enforce=LOW (bloquear TODO RAW SQL fora do helper)

**Meta Final:**
- 0 RAW SQL fora do helper
- 100% isolamento de tenants

---

## ✅ CHECKLIST DE VALIDAÇÃO

### Implementação

- [x] Exceção `RawSQLEnforcementError` criada
- [x] Flag `SQL_AUDIT_ENFORCE` lida do ambiente
- [x] Flag `SQL_AUDIT_ENFORCE_LEVEL` lida do ambiente
- [x] Validação de `SQL_AUDIT_ENFORCE_LEVEL` (HIGH/MEDIUM/LOW)
- [x] Log de configuração ao inicializar
- [x] Lógica de threshold implementada
- [x] Bloqueio lança `RawSQLEnforcementError`
- [x] Mensagem de erro clara e útil
- [x] Log estruturado de bloqueio (`raw_sql_blocked`)
- [x] Helper tenant-safe NUNCA é bloqueado
- [x] Funções `is_enforcement_enabled()` e `get_enforcement_config()`

---

### Comportamento

#### Enforcement Desativado (Default)

- [x] `SQL_AUDIT_ENFORCE=false` (default) → Não bloqueia nada
- [x] Queries HIGH risk apenas logadas
- [x] Aplicação funciona normalmente

#### Enforcement Ativado

- [x] `SQL_AUDIT_ENFORCE=true` + `LEVEL=HIGH` → Bloqueia HIGH
- [x] Queries MEDIUM e LOW permitidas
- [x] Helper tenant-safe sempre permitido
- [x] Exceção `RawSQLEnforcementError` lançada
- [x] Mensagem de erro mostra arquivo, linha, tabelas
- [x] Mensagem de erro sugere uso do helper

#### Edge Cases

- [x] Helper com RAW SQL interno → Não bloqueia
- [x] Query LOW em modo Enforce=HIGH → Permite
- [x] Query MEDIUM em modo Enforce=HIGH → Permite
- [x] Query HIGH em modo Enforce=MEDIUM → Bloqueia
- [x] `SQL_AUDIT_ENFORCE_LEVEL` inválido → Default para HIGH

---

### Testes Unitários

- [x] Teste: Enforcement desativado → Não bloqueia
- [x] Teste: Enforcement HIGH → Bloqueia HIGH
- [x] Teste: Enforcement HIGH → Permite MEDIUM
- [x] Teste: Enforcement HIGH → Permite LOW
- [x] Teste: Helper tenant-safe → Sempre permite
- [x] Teste: Mensagem de erro contém arquivo/tabela
- [x] Teste: Log estruturado de bloqueio

---

### Testes Integração

- [ ] Teste: Endpoint com query HIGH bloqueada → 500
- [ ] Teste: Endpoint com helper → 200
- [ ] Teste: Rollback enforcement → 200

---

### Rollout

- [ ] Fase 1: Dev local (1-2 semanas)
- [ ] Fase 2: Staging (1 semana)
- [ ] Fase 3.1: Produção 10% (1 semana)
- [ ] Fase 3.2: Produção 50% (1 semana)
- [ ] Fase 3.3: Produção 100% (1 semana)

---

## 🔍 MONITORAMENTO

### Métricas a Observar

#### 1. Taxa de Bloqueio

```python
from app.db.sql_audit import get_audit_stats

stats = get_audit_stats()

# Queries bloqueadas por hora
blocked_per_hour = stats["HIGH"] * (60 / snapshot_interval)
```

**Threshold:**
- Desenvolvimento: Ilimitado (esperado)
- Staging: <50/hora
- Produção: <5/hora (idealmente 0)

---

#### 2. Taxa de Erro 500

**Query Prometheus:**
```promql
rate(http_requests_total{status="500"}[5m])
```

**Threshold:**
- <0.1% de requests

**Alertar se:** Taxa de erro 500 aumenta após ativar enforcement

---

#### 3. Logs de Bloqueio

**Buscar no Elasticsearch/Loki:**
```
event: "raw_sql_blocked"
risk_level: "HIGH"
```

**Análise:**
- Quais arquivos mais bloqueados?
- Quais tabelas mais afetadas?
- Horário de pico?

---

### Dashboards

#### Dashboard 1: Enforcement Status

```
┌───────────────────────────────────────────┐
│ SQL AUDIT ENFORCEMENT                     │
├───────────────────────────────────────────┤
│ Status:     ACTIVE                        │
│ Level:      HIGH                          │
│ Blocks:     HIGH+ risk queries            │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│ QUERIES LAST 24H                          │
├───────────────────────────────────────────┤
│ Total:      1,234                         │
│ HIGH:         89 ( 7.2%) → 🔴 BLOCKED     │
│ MEDIUM:      456 (37.0%) → ✅ ALLOWED     │
│ LOW:         689 (55.8%) → ✅ ALLOWED     │
└───────────────────────────────────────────┘
```

---

#### Dashboard 2: Top Blocked Queries

```
┌───────────────────────────────────────────┐
│ TOP FILES BLOCKED                         │
├───────────────────────────────────────────┤
│ 1. comissoes_routes.py       42 blocks   │
│ 2. relatorio_vendas.py       25 blocks   │
│ 3. relatorio_dre.py          15 blocks   │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│ TOP TABLES AFFECTED                       │
├───────────────────────────────────────────┤
│ 1. comissoes_itens           35 blocks   │
│ 2. vendas                    28 blocks   │
│ 3. produtos                  18 blocks   │
└───────────────────────────────────────────┘
```

---

## 🚨 TROUBLESHOOTING

### Problema 1: Query legítima sendo bloqueada

**Sintoma:**
```
RawSQLEnforcementError: HIGH risk query detected
📊 Tables: tenants
```

**Causa:** Tabela `tenants` não está na whitelist

**Solução:**
```python
# app/db/sql_audit.py
WHITELIST_TABLES = {
    "tenants",  # ✅ Adicionar aqui
    # ...
}
```

---

### Problema 2: Helper sendo bloqueado incorretamente

**Sintoma:**
```python
execute_tenant_safe(db, "SELECT * FROM vendas WHERE {tenant_filter}")
# RawSQLEnforcementError ???
```

**Causa:** Stack trace não detectou helper

**Debug:**
```python
# Verificar se helper está no call stack
import traceback
print("".join(traceback.format_stack()))
# Deve conter "tenant_safe_sql.py"
```

**Solução:** Verificar função `_is_from_tenant_safe_helper()`

---

### Problema 3: Enforcement não está ativando

**Sintoma:**
```bash
SQL_AUDIT_ENFORCE=true
# Mas queries HIGH não são bloqueadas
```

**Debug:**
```python
from app.db.sql_audit import is_enforcement_enabled, get_enforcement_config

print(is_enforcement_enabled())  # Deve ser True
print(get_enforcement_config())
# {
#     "enabled": False,  # ❌ PROBLEMA!
#     "level": "HIGH",
#     "blocks": "none"
# }
```

**Causas possíveis:**
1. Variável de ambiente não foi exportada
2. Aplicação foi iniciada antes de setar variável
3. Typo no nome da variável

**Solução:**
```bash
# Exportar corretamente
export SQL_AUDIT_ENFORCE=true

# Reiniciar aplicação
docker-compose restart backend
```

---

### Problema 4: Muitos bloqueios em produção

**Sintoma:** 100+ queries HIGH bloqueadas por hora

**Causa:** Ainda existem queries não migradas

**Solução imediata:**
```bash
# ROLLBACK: Desativar enforcement
SQL_AUDIT_ENFORCE=false
docker-compose restart backend
```

**Solução definitiva:**
1. Identificar queries bloqueadas nos logs
2. Migrar para helper tenant-safe
3. Re-ativar enforcement

---

## 📚 REFERÊNCIAS

- [CHANGES_SQL_AUDIT_P0_A.md](CHANGES_SQL_AUDIT_P0_A.md) - Hook de Auditoria
- [CHANGES_SQL_AUDIT_P0_B.md](CHANGES_SQL_AUDIT_P0_B.md) - Classificação de Risco
- [CHANGES_SQL_AUDIT_P0_C.md](CHANGES_SQL_AUDIT_P0_C.md) - Métricas
- [CHANGES_RAW_SQL_INFRA_P0.md](CHANGES_RAW_SQL_INFRA_P0.md) - Helper tenant-safe
- [RAW_SQL_INVENTORY.md](RAW_SQL_INVENTORY.md) - 129 queries mapeadas

---

## 🎯 RESUMO EXECUTIVO

### O que foi implementado

✅ **Exceção `RawSQLEnforcementError`** - Bloqueio de queries HIGH risk  
✅ **Flag `SQL_AUDIT_ENFORCE`** - Ativar/desativar enforcement  
✅ **Flag `SQL_AUDIT_ENFORCE_LEVEL`** - Threshold de bloqueio (HIGH/MEDIUM/LOW)  
✅ **Lógica de threshold** - Compara risco com nível de enforcement  
✅ **Mensagem de erro clara** - Mostra arquivo, tabela, solução  
✅ **Log estruturado** - Evento `raw_sql_blocked`  
✅ **Helper nunca bloqueado** - `_is_from_tenant_safe_helper()` protege  

### Por que importa

- 🔒 **Prevenção proativa** - Bloqueia vazamentos ANTES de acontecerem
- 🎯 **Enforcement gradual** - Rollout controlado (dev → staging → prod)
- 🛡️ **Zero-trust** - Força uso do helper tenant-safe
- 📊 **Observabilidade** - Logs mostram o que seria bloqueado

### Próxima ação

**Fase 1: Desenvolvimento Local (1-2 semanas)**
1. Ativar enforcement no .env local:
   ```bash
   SQL_AUDIT_ENFORCE=true
   SQL_AUDIT_ENFORCE_LEVEL=HIGH
   ```
2. Testar aplicação completa
3. Migrar queries bloqueadas → helper
4. Validar 0 queries HIGH risk

**Fase 2: Staging → Produção (3-4 semanas)**
- Seguir plano de rollout gradual
- Monitorar taxa de erro 500
- Ajustar whitelist se necessário

---

**Status Final:** ✅ **ENFORCEMENT IMPLEMENTADO E PRONTO PARA ROLLOUT**

**Default:** Enforcement desativado (apenas logging)  
**Ativação:** Via `SQL_AUDIT_ENFORCE=true`  
**Rollout:** Gradual (local → staging → prod 10% → 50% → 100%)
