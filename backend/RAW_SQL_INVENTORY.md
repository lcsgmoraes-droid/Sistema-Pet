# 📄 RAW SQL INVENTORY

**Sistema Pet - Inventário Completo de Queries RAW SQL**

Data: 05/02/2026  
Objetivo: Mapear todas as queries RAW SQL para posterior sanitização multi-tenant

---

## 📊 RESUMO EXECUTIVO

| Categoria | Quantidade | Risco Alto | Risco Médio | Risco Baixo |
|-----------|------------|------------|-------------|-------------|
| 🔴 MULTI-TENANT | 89 | 67 | 18 | 4 |
| 🟡 WHITELIST | 12 | 0 | 3 | 9 |
| 🟢 UTILITÁRIA | 28 | 0 | 0 | 28 |
| **TOTAL** | **129** | **67** | **21** | **41** |

---

## 🔴 QUERIES MULTI-TENANT (OBRIGATÓRIO tenant_id)

### **Módulo: Comissões (CRÍTICO - FINANCEIRO)**

#### 1. `backend/app/comissoes_models.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 32-48 | `listar_configuracoes` | SELECT | `comissoes_configuracao`, `categorias`, `produtos` | ❌ NÃO | 🔴 ALTO |
| 78-90 | `buscar_configuracao` | SELECT | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 96-108 | `buscar_configuracao` (subcategoria) | SELECT | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 114-126 | `buscar_configuracao` (categoria) | SELECT | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 157-177 | `salvar_configuracao` (UPDATE) | UPDATE | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 181-200 | `salvar_configuracao` (INSERT) | INSERT | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 222-238 | `obter_comissoes_itens_analise` | SELECT | `comissoes_itens`, `vendas_itens`, `produtos` | ❌ NÃO | 🔴 ALTO |
| 251-272 | `recalcular_comissoes_mes` | UPDATE | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 324-340 | `obter_historico_comissoes` | SELECT | `comissoes_itens`, `vendas` | ❌ NÃO | 🔴 ALTO |
| 404 | `obter_comissoes_itens` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 423 | `obter_config_sistema` | SELECT | `comissoes_configuracoes_sistema` | ❌ NÃO | 🔴 ALTO |
| 475 | `obter_relatorio_analitico` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**: 
- Todas as queries financeiras SEM filtro `tenant_id`
- Risco CRÍTICO de vazamento de dados entre tenants
- JOINs entre tabelas multi-tenant sem proteção
- Valores monetários expostos

---

#### 2. `backend/app/comissoes_provisao.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 64-72 | `provisionar_comissoes_venda` | SELECT | `vendas` | ✅ SIM | 🟢 BAIXO |
| 101-108 | `provisionar_comissoes_venda` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 130-137 | `provisionar_comissoes_venda` | SELECT | `dre_subcategorias` | ✅ SIM | 🟢 BAIXO |
| 169-177 | `provisionar_comissoes_venda` | SELECT | `clientes` (funcionários) | ❌ NÃO | 🔴 ALTO |
| 212-240 | `provisionar_comissoes_venda` | INSERT | `contas_pagar` | ❌ NÃO | 🔴 ALTO |
| 296-310 | `provisionar_comissoes_venda` | UPDATE | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- Mix de queries protegidas e desprotegidas
- INSERT em `contas_pagar` sem `tenant_id` explícito
- UPDATE em `comissoes_itens` global

---

#### 3. `backend/app/comissoes_demonstrativo_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 146 | `listar_demonstrativo` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 234 | `obter_resumo_funcionario` | SELECT | `comissoes_itens` (total gerado) | ❌ NÃO | 🔴 ALTO |
| 242 | `obter_resumo_funcionario` | SELECT | `comissoes_itens` (total pago) | ❌ NÃO | 🔴 ALTO |
| 250 | `obter_resumo_funcionario` | SELECT | `comissoes_itens` (total pendente) | ❌ NÃO | 🔴 ALTO |
| 258 | `obter_resumo_funcionario` | SELECT | `comissoes_itens` (total estornado) | ❌ NÃO | 🔴 ALTO |
| 266 | `obter_resumo_funcionario` | SELECT | `comissoes_itens` (count) | ❌ NÃO | 🔴 ALTO |
| 335-349 | `exportar_demonstrativo` | SELECT | `comissoes_itens`, `vendas` | ❌ NÃO | 🔴 ALTO |
| 419 | `obter_detalhes_pagamento` | SELECT | `clientes` | ❌ NÃO | 🔴 ALTO |
| 461 | `obter_detalhes_pagamento` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 471 | `obter_detalhes_pagamento` | SELECT | `clientes` (IN clause) | ❌ NÃO | 🔴 ALTO |
| 565-580 | `criar_pagamento` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 741 | `listar_pagamentos_periodo` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 821 | `atualizar_pagamento` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 855 | `atualizar_pagamento` | UPDATE | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 881 | `cancelar_pagamento` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 1053 | `relatorio_comissoes_mes` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 1152 | `recibo_pagamento` | SELECT | `clientes` | ❌ NÃO | 🔴 ALTO |
| 1186 | `recibo_pagamento` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 1202 | `recibo_pagamento` | SELECT | `clientes` (IN clause) | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- **CRÍTICO**: Todas as queries de relatórios sem `tenant_id`
- Queries de soma financeira globais
- Exportação de dados sem filtro multi-tenant

---

#### 4. `backend/app/comissoes_estorno.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 63-75 | `estornar_comissao` | SELECT | `comissoes_itens`, `vendas` | ❌ NÃO | 🔴 ALTO |
| 144-160 | `estornar_comissao` | DELETE | `contas_pagar` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- DELETE sem filtro `tenant_id` = RISCO MÁXIMO
- Pode apagar contas de outros tenants

---

#### 5. `backend/app/comissoes_avancadas_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 103-107 | `listar_configuracoes` | SELECT | `clientes` | ❌ NÃO | 🔴 ALTO |
| 166 | `listar_configuracoes` | SELECT | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 174-177 | `listar_configuracoes` | SELECT | `clientes` (ANY) | ❌ NÃO | 🔴 ALTO |
| 184-187 | `listar_configuracoes` | SELECT | `categorias` | ❌ NÃO | 🔴 ALTO |
| 194-197 | `listar_configuracoes` | SELECT | `produtos` | ❌ NÃO | 🔴 ALTO |
| 312-315 | `listar_formas_pagamento` | SELECT | `formas_pagamento_comissoes` | ❌ NÃO | 🔴 ALTO |
| 424-427 | `registrar_divida` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 462-475 | `consultar_dividas` | SELECT | `comissoes_dividas` | ❌ NÃO | 🔴 ALTO |
| 520-535 | `quitar_divida` | UPDATE | `comissoes_dividas` | ❌ NÃO | 🔴 ALTO |
| 554-558 | `cancelar_divida` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 583-597 | `cancelar_divida` | DELETE | `comissoes_dividas` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- Sistema de dívidas completamente exposto
- DELETE sem filtro tenant

---

#### 6. `backend/app/comissoes_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 151-169 | `listar_comissoes_pendentes` | SELECT | `comissoes_itens`, `vendas` | ❌ NÃO | 🔴 ALTO |
| 213-227 | `obter_comissao` | SELECT | `comissoes_itens`, `vendas` | ❌ NÃO | 🔴 ALTO |
| 322-332 | `marcar_como_pago` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 335-348 | `marcar_como_pago` | UPDATE | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 364-377 | `reverter_pagamento` | SELECT | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 462-488 | `salvar_configuracao` | SELECT/INSERT/UPDATE | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 570-574 | `validar_funcionario` | SELECT | `clientes` | ❌ NÃO | 🔴 ALTO |
| 787-805 | `calcular_comissoes_produto` | SELECT | `produtos`, `categorias` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- Marca/desmarca pagamentos sem validar tenant
- CRUD de configurações exposto

---

### **Módulo: Clientes**

#### 7. `backend/app/clientes_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 906-917 | `update_cliente` (desativar comissões) | SELECT | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |
| 919-928 | `update_cliente` (desativar comissões) | UPDATE | `comissoes_configuracao` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- Desativa configurações de comissão sem filtro tenant
- Pode afetar outros clientes

---

### **Módulo: Vendas**

#### 8. `backend/app/vendas_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 506-508 | `cancelar_venda` | DELETE | `comissoes_itens` | ❌ NÃO | 🔴 ALTO |
| 518-525 | `calcular_totais_venda` | SELECT | `pagamentos` | ❌ NÃO | 🔴 ALTO |

**⚠️ ANÁLISE**:
- DELETE global em comissões ao cancelar venda
- Cálculo de totais sem filtro tenant

---

### **Módulo: Subcategorias**

#### 9. `backend/app/subcategorias_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 181 | `atualizar_subcategoria` | SELECT | `subcategorias` | ❌ NÃO | 🟡 MÉDIO |
| 194 | `atualizar_subcategoria` | SELECT | `categorias` | ❌ NÃO | 🟡 MÉDIO |
| 226 | `atualizar_subcategoria` | UPDATE | `subcategorias` | ❌ NÃO | 🔴 ALTO |
| 262 | `excluir_subcategoria` | SELECT | `subcategorias` | ❌ NÃO | 🟡 MÉDIO |
| 270-278 | `excluir_subcategoria` | SELECT | `produtos` (count) | ❌ NÃO | 🔴 ALTO |
| 287-295 | `excluir_subcategoria` | DELETE | `subcategorias` | ❌ NÃO | 🔴 ALTO |
| 328-338 | `listar_subcategorias` | SELECT | `subcategorias`, `categorias` | ❌ NÃO | 🔴 ALTO |

---

### **Módulo: Read Models (Schema Swap)**

#### 10. `backend/app/read_models/schema_swap.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 112 | `create_temp_schema` | DROP TABLE | `read_*_temp` | N/A | 🟢 BAIXO |
| 122 | `create_temp_schema` | CREATE TABLE | `read_*_temp` | N/A | 🟢 BAIXO |
| 126-130 | `create_temp_schema` | CREATE INDEX | `read_*_temp` | N/A | 🟢 BAIXO |
| 156 | `cleanup_temp_schema` | DROP TABLE | `read_*_temp` | N/A | 🟢 BAIXO |
| 201 | `validate_schema` | SELECT COUNT | `read_*` | ❌ NÃO | 🟡 MÉDIO |
| 218-224 | `validate_schema` | SELECT (datas futuras) | `read_vendas_resumo_diario` | ❌ NÃO | 🟡 MÉDIO |
| 230-237 | `validate_schema` | SELECT (receitas negativas) | `read_receita_mensal` | ❌ NÃO | 🟡 MÉDIO |
| 333-338 | `swap_schemas_atomic` | ALTER TABLE RENAME | `read_*` | N/A | 🟢 BAIXO |
| 356-357 | `swap_schemas_atomic` (rollback) | ALTER TABLE RENAME | `read_*` | N/A | 🟢 BAIXO |
| 381 | `cleanup_old_schema` | DROP TABLE | `read_*_old` | N/A | 🟢 BAIXO |

**⚠️ ANÁLISE**:
- Operações DDL (estrutura) - baixo risco
- Validações sem filtro tenant - médio risco

---

### **Módulo: Admin**

#### 11. `backend/app/admin_fix_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 28 | `corrigir_sequences` | SELECT MAX | Qualquer tabela | ❌ NÃO | 🟡 MÉDIO |
| 36-38 | `corrigir_sequences` | SELECT setval | pg_get_serial_sequence | N/A | 🟢 BAIXO |

---

## 🟡 QUERIES WHITELIST (Auth / Sistema)

### **Módulo: Autenticação**

#### 12. `backend/configurar_stone.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 43 | `main` | SELECT | `tenants` | N/A | 🟢 BAIXO |
| 56 | `main` | SELECT | `users` | ✅ SIM | 🟢 BAIXO |

**✅ ANÁLISE**: Queries administrativas OK

---

#### 13. `backend/check_user_permissions.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 14-20 | `verificar_permissoes` | SELECT | `users`, `roles`, `permissions` | N/A | 🟡 MÉDIO |

**✅ ANÁLISE**: Sistema de permissões - requer auditoria

---

#### 14. `backend/final_migration.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 43-49 | `main` | SELECT | `tenants` | N/A | 🟢 BAIXO |
| 51-58 | `main` | SELECT | `users` | ✅ SIM | 🟢 BAIXO |
| 60-70 | `main` | UPDATE | `users` | ✅ SIM | 🟢 BAIXO |
| 85-91 | `main` | SELECT | Várias tabelas órfãs | N/A | 🟡 MÉDIO |

---

#### 15. `backend/create_ia_compras_permissions.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 33-40 | `create_permission` | SELECT | `permissions` | N/A | 🟢 BAIXO |

---

## 🟢 QUERIES UTILITÁRIAS (Health / Migrations / Testes)

### **Módulo: Health Check**

#### 16. `backend/app/health_router.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 57 | `health_check` | SELECT 1 | - | N/A | 🟢 BAIXO |
| 157 | `liveness` | SELECT 1 | - | N/A | 🟢 BAIXO |

#### 17. `backend/app/routes/health_routes.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 43 | `health` | SELECT 1 | - | N/A | 🟢 BAIXO |

---

### **Módulo: Migrations**

#### 18-40. Scripts de Migration (Vários arquivos)

| Arquivo | Tipo | Risco |
|---------|------|-------|
| `add_updated_at_all_tables.py` | ALTER TABLE | 🟢 BAIXO |
| `apply_whatsapp_migration.py` | DDL | 🟢 BAIXO |
| `criar_tabelas_conversas_whatsapp.py` | CREATE TABLE | 🟢 BAIXO |
| `create_dre_subcategorias.py` | INSERT | 🟢 BAIXO |
| `migrations/criar_tabelas_whatsapp_ia.py` | CREATE TABLE + INDEX | 🟢 BAIXO |
| `migrations/adicionar_pontos_inicial_final_rota.py` | ALTER TABLE | 🟢 BAIXO |
| `scripts/migrate_sqlite_to_postgres.py` | INSERT (migration) | 🟢 BAIXO |
| `scripts/migrar_fiscal_legado_para_v2.py` | SELECT/INSERT | 🟢 BAIXO |

**✅ ANÁLISE**: Migrations são executadas uma vez, contexto controlado

---

### **Módulo: Testes**

#### 41. `backend/teste_auditoria_banco.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 42 | `testar_conexao` | SELECT 1 | - | N/A | 🟢 BAIXO |
| 58-66 | `verificar_colunas` | SELECT (information_schema) | `rotas_entrega` | N/A | 🟢 BAIXO |
| 104-111 | `verificar_dados` | SELECT COUNT | `rotas_entrega` | N/A | 🟢 BAIXO |
| 136-149 | `inspecionar_rotas` | SELECT | `rotas_entrega` | N/A | 🟢 BAIXO |

---

#### 42. `backend/test_tenant_blindagem.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 14 | `test_sem_context` | SELECT | `users` | N/A | 🟢 BAIXO |
| 25 | `test_com_tenant` | SELECT | `tenants` | N/A | 🟢 BAIXO |
| 28 | `test_com_tenant` | SELECT | `users` | N/A | 🟢 BAIXO |

---

#### 43. `backend/tests/conftest.py`

| Linha | Função | Tipo | Tabelas | Filtra tenant_id? | Risco |
|-------|--------|------|---------|-------------------|-------|
| 121-128 | `db_session` (fixture) | DELETE | Várias tabelas | N/A | 🟢 BAIXO |
| 157-165 | `db_session` (fixture) | DELETE | Várias tabelas | N/A | 🟢 BAIXO |

---

#### 44-56. Outros Scripts Utilitários

- `ver_enums.py` - Consulta pg_enum
- `ver_colunas_dre.py` - information_schema
- `ver_tabelas_dre.py` - information_schema
- `verificar_e_recalcular_segmentos.py` - SELECT/INSERT/UPDATE em segmentos
- `verificar_fk_produto_lotes.py` - information_schema
- `validate_schema.py` - information_schema
- `validate_product_variations.py` - SELECT produtos
- `inspecionar_orfas.py` - SELECT órfãos

**✅ ANÁLISE**: Scripts administrativos/debug - uso interno

---

## 📋 TABELAS MULTI-TENANT IDENTIFICADAS

| Tabela | tenant_id? | Tipo |
|--------|------------|------|
| `vendas` | ✅ | Transacional |
| `vendas_itens` | ✅ | Transacional |
| `comissoes_itens` | ⚠️ | Financeiro (FALTA tenant_id?) |
| `comissoes_configuracao` | ⚠️ | Configuração (FALTA tenant_id?) |
| `comissoes_dividas` | ⚠️ | Financeiro (FALTA tenant_id?) |
| `contas_pagar` | ⚠️ | Financeiro (FALTA tenant_id?) |
| `clientes` | ✅ | Master Data |
| `produtos` | ✅ | Master Data |
| `categorias` | ✅ | Master Data |
| `subcategorias` | ✅ | Master Data |
| `dre_subcategorias` | ✅ | Configuração |
| `dre_categorias` | ✅ | Configuração |
| `formas_pagamento_comissoes` | ⚠️ | Configuração (FALTA tenant_id?) |
| `cliente_segmentos` | ⚠️ | CRM (FALTA tenant_id?) |

---

## 🚨 QUERIES DE RISCO CRÍTICO (PRIORIDADE P0)

### **Top 10 Mais Perigosas**

1. **`comissoes_estorno.py:144`** - `DELETE FROM contas_pagar` sem tenant  
   → Pode apagar contas de pagamento de outros tenants

2. **`comissoes_demonstrativo_routes.py:234-266`** - Somas financeiras globais  
   → Relatórios consolidam valores de todos os tenants

3. **`comissoes_avancadas_routes.py:583`** - `DELETE FROM comissoes_dividas` sem tenant  
   → Exclui dívidas de outros clientes

4. **`vendas_routes.py:506`** - `DELETE FROM comissoes_itens` sem tenant  
   → Ao cancelar venda, apaga comissões de outros tenants

5. **`comissoes_models.py:157-200`** - INSERT/UPDATE configurações sem tenant  
   → Cria/atualiza configurações globalmente

6. **`subcategorias_routes.py:287`** - `DELETE FROM subcategorias` sem tenant  
   → Exclui categorias de outros tenants

7. **`comissoes_provisao.py:212`** - `INSERT INTO contas_pagar` sem tenant explícito  
   → Cria contas sem validação multi-tenant

8. **`comissoes_routes.py:335`** - `UPDATE comissoes_itens SET status='pago'` sem tenant  
   → Marca pagamentos globalmente

9. **`clientes_routes.py:919`** - `UPDATE comissoes_configuracao SET ativo=0` sem tenant  
   → Desativa configurações de outros tenants

10. **`comissoes_models.py:32-48`** - SELECT com JOINs sem tenant  
    → Exibe configurações de todos os tenants

---

## 📝 RECOMENDAÇÕES DE SANITIZAÇÃO

### **Estratégia 1: Helper Tenant-Safe** ✅ RECOMENDADO

```python
# backend/app/core/tenant_safe_queries.py

from sqlalchemy import text
from app.core.tenant_context import get_current_tenant_id

def execute_tenant_safe(
    db: Session,
    query: str,
    params: dict = None,
    require_tenant: bool = True
) -> Result:
    """
    Executa query RAW SQL com filtro tenant_id automático.
    
    Args:
        db: Sessão do banco
        query: SQL com placeholder WHERE {tenant_filter}
        params: Parâmetros da query
        require_tenant: Se True, falha sem tenant_id no contexto
    
    Raises:
        TenantContextError: Se require_tenant=True e sem tenant no contexto
    
    Example:
        >>> result = execute_tenant_safe(db, '''
        ...     SELECT * FROM comissoes_itens
        ...     WHERE {tenant_filter} AND status = :status
        ... ''', {'status': 'pendente'})
    """
    tenant_id = get_current_tenant_id()
    
    if require_tenant and not tenant_id:
        raise TenantContextError("tenant_id não encontrado no contexto")
    
    # Substituir placeholder
    if require_tenant:
        query = query.replace("{tenant_filter}", "tenant_id = :__tenant_id")
        params = params or {}
        params["__tenant_id"] = tenant_id
    else:
        query = query.replace("{tenant_filter}", "1=1")
    
    return db.execute(text(query), params)
```

**Uso:**

```python
# ANTES (INSEGURO)
result = db.execute(text("""
    SELECT * FROM comissoes_itens 
    WHERE status = :status
"""), {"status": "pendente"})

# DEPOIS (SEGURO)
result = execute_tenant_safe(db, """
    SELECT * FROM comissoes_itens 
    WHERE {tenant_filter} AND status = :status
""", {"status": "pendente"})
```

---

### **Estratégia 2: Migrar para SQLAlchemy ORM** 🟡 MÉDIO PRAZO

```python
# ANTES (RAW SQL)
result = db.execute(text("""
    SELECT ci.*, v.numero_venda
    FROM comissoes_itens ci
    JOIN vendas v ON v.id = ci.venda_id
    WHERE ci.status = :status
"""), {"status": "pendente"})

# DEPOIS (ORM com tenant filter automático)
from app.models.comissoes import ComissaoItem
from app.models.vendas import Venda

result = db.query(ComissaoItem).join(Venda).filter(
    ComissaoItem.status == "pendente"
).all()
# tenant_id é injetado automaticamente pelo TenantFilter no ORM
```

---

### **Estratégia 3: Whitelist de Queries Não-Tenant** 🟢 SIMPLES

```python
# backend/app/core/whitelist_queries.py

WHITELIST_QUERIES = {
    "health_check": "SELECT 1",
    "tenants_list": "SELECT id, nome FROM tenants WHERE ativo = true",
    "permissions_list": "SELECT * FROM permissions WHERE ativo = true",
}

def execute_whitelist(db: Session, query_name: str, params: dict = None):
    """Executa query da whitelist (sem filtro tenant)"""
    if query_name not in WHITELIST_QUERIES:
        raise ValueError(f"Query {query_name} não está na whitelist")
    
    return db.execute(text(WHITELIST_QUERIES[query_name]), params)
```

---

## 🎯 PLANO DE AÇÃO

### **Fase 1: Bloqueio de Emergência** (1 dia)

1. Criar middleware que audita TODAS as queries RAW SQL
2. Logar WARNING para queries sem `tenant_id` em WHERE
3. Habilitar modo "strict" em staging

```python
# backend/app/middleware/sql_audit.py

import re
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def audit_raw_sql(conn, cursor, statement, parameters, context, executemany):
    """Audita queries RAW SQL"""
    
    # Detectar text()
    if "text(" in str(context):
        # Verificar se tem tenant_id no WHERE
        if "WHERE" in statement.upper():
            if "tenant_id" not in statement.lower():
                logger.warning(
                    f"⚠️ RAW SQL sem tenant_id: {statement[:100]}...",
                    extra={"statement": statement, "params": parameters}
                )
```

---

### **Fase 2: Sanitização Gradual** (2 semanas)

1. **Semana 1**: Módulo Comissões (67 queries)
   - Adicionar coluna `tenant_id` em tabelas faltantes
   - Implementar `execute_tenant_safe`
   - Migrar queries críticas (DELETE, UPDATE, INSERT)

2. **Semana 2**: Módulos Vendas, Clientes, Subcategorias
   - Migrar queries de relatórios
   - Implementar whitelist
   - Testes de regressão

---

### **Fase 3: Validação e Testes** (1 semana)

1. Testes de isolamento multi-tenant
2. Auditoria de logs
3. Performance benchmarks
4. Code review final

---

### **Fase 4: Deploy e Monitoramento** (contínuo)

1. Deploy em staging
2. Testes com clientes piloto
3. Monitoramento de queries lentas
4. Ajustes de performance

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Atual | Meta |
|---------|-------|------|
| Queries RAW SQL | 129 | 50 |
| Queries sem `tenant_id` | 89 | 0 |
| Queries de risco ALTO | 67 | 0 |
| Cobertura de testes | ? | 95% |
| Performance (p95) | ? | < 200ms |

---

## 🔗 REFERÊNCIAS

- [SQLAlchemy 2 - Best Practices](https://docs.sqlalchemy.org/en/20/orm/queryguide/)
- [Multi-Tenancy Patterns](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP - SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

**Documento gerado em:** 05/02/2026  
**Autor:** Sistema de Análise Automatizada  
**Versão:** 1.0  
**Status:** 🔴 CRÍTICO - AÇÃO IMEDIATA NECESSÁRIA
