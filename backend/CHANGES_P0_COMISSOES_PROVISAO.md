# Migração P0 – comissoes_provisao.py

**Arquivo**: `app/comissoes_provisao.py`  
**Data**: 2026-02-05  
**Objetivo**: Eliminar TODAS as queries RAW SQL de RISCO ALTO (HIGH), substituindo por `execute_tenant_safe()`

---

## ✅ Resultado da Auditoria

```
HIGH = 0 para comissoes_provisao.py
```

**Status**: ✅ **TODAS as queries RAW SQL foram migradas com sucesso**

---

## 📊 Resumo

- **Arquivo migrado**: `app/comissoes_provisao.py`
- **Total de queries RAW encontradas**: 7
- **Queries migradas para tenant-safe**: 7
- **Taxa de sucesso**: 100%

---

## 📋 Detalhamento das Migrações

### 1️⃣ SELECT - Buscar venda e validar (linha 65)

**Finalidade**: Validar existência e status da venda antes de provisionar comissões

**Antes:**
```python
result_venda = db.execute(text("""
    SELECT 
        v.id, v.numero_venda, v.data_venda, v.canal,
        v.cliente_id, v.status
    FROM vendas v
    WHERE v.id = :venda_id AND v.tenant_id = :tenant_id
"""), {'venda_id': venda_id, 'tenant_id': tenant_id})
```

**Depois:**
```python
result_venda = execute_tenant_safe(db, """
    SELECT 
        v.id, v.numero_venda, v.data_venda, v.canal,
        v.cliente_id, v.status
    FROM vendas v
    WHERE v.id = :venda_id AND {tenant_filter}
""", {'venda_id': venda_id})
```

**Impacto**: ✅ Removido `tenant_id` explícito do WHERE, substituído por `{tenant_filter}` automático

---

### 2️⃣ SELECT - Buscar comissões não provisionadas (linha 102)

**Finalidade**: Listar todas as comissões da venda que ainda não foram provisionadas

**Antes:**
```python
result_comissoes = db.execute(text("""
    SELECT 
        id, funcionario_id, valor_comissao_gerada, produto_id
    FROM comissoes_itens
    WHERE venda_id = :venda_id
      AND comissao_provisionada = 0
      AND valor_comissao_gerada > 0
"""), {'venda_id': venda_id})
```

**Depois:**
```python
result_comissoes = execute_tenant_safe(db, """
    SELECT 
        id, funcionario_id, valor_comissao_gerada, produto_id
    FROM comissoes_itens
    WHERE venda_id = :venda_id
      AND comissao_provisionada = 0
      AND valor_comissao_gerada > 0
      AND {tenant_filter}
""", {'venda_id': venda_id})
```

**Impacto**: ✅ Adicionado `{tenant_filter}` para garantir isolamento multi-tenant

---

### 3️⃣ SELECT - Buscar subcategoria DRE "Comissões" (linha 132)

**Finalidade**: Obter ID da subcategoria DRE para classificar a despesa de comissão

**Antes:**
```python
result_subcat = db.execute(text("""
    SELECT id
    FROM dre_subcategorias
    WHERE tenant_id = :tenant_id
      AND nome = 'Comissões'
      AND ativo = 1
    LIMIT 1
"""), {'tenant_id': tenant_id})
```

**Depois:**
```python
result_subcat = execute_tenant_safe(db, """
    SELECT id
    FROM dre_subcategorias
    WHERE nome = 'Comissões'
      AND ativo = 1
      AND {tenant_filter}
    LIMIT 1
""", {})
```

**Impacto**: ✅ Removido `tenant_id` explícito, substituído por `{tenant_filter}` automático

---

### 4️⃣ SELECT - Buscar dados do funcionário (linha 171)

**Finalidade**: Obter nome e data de fechamento de comissão do funcionário comissionado

**Antes:**
```python
result_func = db.execute(text("""
    SELECT nome, data_fechamento_comissao
    FROM users
    WHERE id = :funcionario_id
"""), {'funcionario_id': funcionario_id})
```

**Depois:**
```python
result_func = execute_tenant_safe(db, """
    SELECT nome, data_fechamento_comissao
    FROM users
    WHERE id = :funcionario_id
    AND {tenant_filter}
""", {'funcionario_id': funcionario_id})
```

**Impacto**: ✅ Adicionado `{tenant_filter}` para garantir isolamento multi-tenant

---

### 5️⃣ INSERT - Criar Conta a Pagar (linha 215)

**Finalidade**: Criar conta a pagar para a comissão provisionada

**Antes:**
```python
db.execute(text("""
    INSERT INTO contas_pagar (
        descricao, fornecedor_id, dre_subcategoria_id, canal,
        valor_original, valor_pago, valor_final,
        data_emissao, data_vencimento, status,
        documento, observacoes, user_id, tenant_id,
        created_at, updated_at
    ) VALUES (
        :descricao, :fornecedor_id, :dre_subcategoria_id, :canal,
        :valor, 0, :valor,
        :data_emissao, :data_vencimento, 'pendente',
        :documento, :observacoes, :user_id, :tenant_id,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
"""), {
    'descricao': descricao_conta,
    'fornecedor_id': funcionario_id,
    ...
    'tenant_id': tenant_id
})
```

**Depois:**
```python
execute_tenant_safe(db, """
    INSERT INTO contas_pagar (
        descricao, fornecedor_id, dre_subcategoria_id, canal,
        valor_original, valor_pago, valor_final,
        data_emissao, data_vencimento, status,
        documento, observacoes, user_id, tenant_id,
        created_at, updated_at
    ) VALUES (
        :descricao, :fornecedor_id, :dre_subcategoria_id, :canal,
        :valor, 0, :valor,
        :data_emissao, :data_vencimento, 'pendente',
        :documento, :observacoes, :user_id, {tenant_id},
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
""", {
    'descricao': descricao_conta,
    'fornecedor_id': funcionario_id,
    ...
    # tenant_id removido dos parâmetros
})
```

**Impacto**: ✅ Substituído `:tenant_id` por `{tenant_id}` (placeholder literal expandido pelo helper)

---

### 6️⃣ SELECT - Obter ID da conta criada (linha 265)

**Finalidade**: Obter ID da conta a pagar recém-criada (SQLite last_insert_rowid)

**Antes:**
```python
result_conta_id = db.execute(text("SELECT last_insert_rowid()"))
```

**Depois:**
```python
result_conta_id = execute_tenant_safe(db, "SELECT last_insert_rowid()", {}, require_tenant=False)
```

**Impacto**: ✅ Query de sistema (não relacionada a tenant), usa `require_tenant=False` para bypass seguro

**Nota**: `last_insert_rowid()` é uma função SQLite que retorna o último ID inserido na sessão atual

---

### 7️⃣ UPDATE - Marcar comissão como provisionada (linha 298)

**Finalidade**: Atualizar flag de provisionamento e vincular conta a pagar

**Antes:**
```python
db.execute(text("""
    UPDATE comissoes_itens
    SET comissao_provisionada = 1,
        conta_pagar_id = :conta_pagar_id,
        data_provisao = :data_provisao
    WHERE id = :comissao_id
"""), {
    'conta_pagar_id': conta_pagar_id,
    'data_provisao': date.today(),
    'comissao_id': comissao_id
})
```

**Depois:**
```python
execute_tenant_safe(db, """
    UPDATE comissoes_itens
    SET comissao_provisionada = 1,
        conta_pagar_id = :conta_pagar_id,
        data_provisao = :data_provisao
    WHERE id = :comissao_id
    AND {tenant_filter}
""", {
    'conta_pagar_id': conta_pagar_id,
    'data_provisao': date.today(),
    'comissao_id': comissao_id
})
```

**Impacto**: ✅ Adicionado `{tenant_filter}` para garantir isolamento multi-tenant

---

## 🔧 Alterações Adicionais

### Import adicionado (linha 18)
```python
from app.utils.tenant_safe_sql import execute_tenant_safe
```

---

## ✅ Verificação de Segurança

| Verificação | Status |
|------------|--------|
| `{tenant_filter}` em SELECT multi-tenant | ✅ 4/4 |
| `{tenant_filter}` em UPDATE multi-tenant | ✅ 1/1 |
| `{tenant_id}` em INSERT | ✅ 1/1 |
| `require_tenant=False` para query de sistema | ✅ 1/1 |
| Sem `db.execute(text())` | ✅ 0 ocorrências |
| Import `execute_tenant_safe` | ✅ Presente |

---

## 🎯 Auditoria

- **SQL_AUDIT_ENFORCE**: `true`
- **SQL_AUDIT_ENFORCE_LEVEL**: `HIGH`
- **Resultado**: ✅ Nenhum bloqueio ocorreu

Todas as queries foram migradas corretamente e respeitam as regras de segurança multi-tenant.

---

## 📋 Checklist

- [x] ✅ Nenhuma f-string em SQL (valores sempre bindados)
- [x] ✅ `{tenant_filter}` literal em queries multi-tenant
- [x] ✅ INSERTs usam `{tenant_id}` placeholder
- [x] ✅ Lógica de negócio preservada (provisão de comissões intacta)
- [x] ✅ Nenhuma refatoração de fluxo
- [x] ✅ Parâmetros sempre bindados
- [x] ✅ Zero queries RAW SQL remanescentes

---

## 📊 Métricas Finais

```
Arquivo: app/comissoes_provisao.py
========================================
Tipo de Query                  | Antes | Depois
-------------------------------|-------|-------
SELECT (multi-tenant)          |   4   |   0
SELECT (sistema, sem tenant)   |   1   |   0
INSERT (multi-tenant)          |   1   |   0
UPDATE (multi-tenant)          |   1   |   0
-------------------------------|-------|-------
Total de queries RAW SQL       |   7   |   0
Total migrado                  |   7   |   7
Taxa de sucesso                | 100%  |
Queries HIGH risk remanescentes|   0   |
```

---

## ✅ Conclusão

**Todos os objetivos da Fase 1.5 foram atingidos:**

1. ✅ Eliminadas TODAS as queries RAW SQL de RISCO ALTO (HIGH)
2. ✅ Substituídas por `execute_tenant_safe()` com `{tenant_filter}` onde aplicável
3. ✅ INSERT usa `{tenant_id}` placeholder corretamente
4. ✅ Query de sistema usa `require_tenant=False` apropriadamente
5. ✅ Preservada toda a lógica de negócio de provisão financeira
6. ✅ Zero queries RAW SQL remanescentes no arquivo

**Status final: SEGURO PARA PRODUÇÃO** 🔒

---

## 📝 Notas Técnicas

### Fluxo de Provisão

O arquivo implementa o fluxo crítico de provisão financeira de comissões:

1. **Validação**: Verifica se venda existe e está efetivada
2. **Comissões**: Busca comissões não provisionadas
3. **DRE**: Busca subcategoria DRE "Comissões"
4. **Loop**: Para cada comissão:
   - Busca dados do funcionário
   - Calcula data de vencimento
   - Cria Conta a Pagar
   - Lança na DRE
   - Marca como provisionada

Toda a lógica foi preservada, apenas as queries foram migradas para o padrão seguro multi-tenant.
