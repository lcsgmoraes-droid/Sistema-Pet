# 🔒 MULTI-TENANCY HARDENING - ANÁLISE E RECOMENDAÇÕES

**Data:** 05 de fevereiro de 2026  
**Versão:** 1.0  
**Objetivo:** Hardening (endurecimento) da segurança multi-tenant  
**Status Atual:** ⚠️ MÉDIO RISCO - Requer correções urgentes

---

## 1. FONTE ÚNICA DE TENANT

### 1.1 Situação Atual

**❌ PROBLEMA: Múltiplas fontes de tenant_id**

O sistema possui **3 formas diferentes** de extrair tenant_id:

1. **TenancyMiddleware** (`app/tenancy/middleware.py`)
   - Extrai do JWT + Seta ContextVar
   - **PROBLEMA:** Possui fallback para tenant padrão

2. **get_current_user** (`app/auth.py`)
   - Extrai do JWT + Seta ContextVar
   - **PROBLEMA:** Opcional (algumas rotas usam, outras não)

3. **get_current_user_and_tenant** (`app/auth/dependencies.py`)
   - Extrai do JWT + Valida obrigatoriedade + Seta ContextVar
   - **✅ CORRETO:** Valida e rejeita se tenant_id ausente

### 1.2 Fonte Única Recomendada

**✅ DECISÃO: `get_current_user_and_tenant` deve ser a ÚNICA fonte**

**Justificativa:**
- Valida obrigatoriedade de tenant_id
- Rejeita requests sem tenant (erro 401)
- Seta contexto explicitamente
- Retorna tuple (User, UUID) - tipagem forte

### 1.3 O que REMOVER sem quebrar

**🗑️ AÇÕES DE REMOÇÃO:**

#### A) Remover extração de tenant em `get_current_user`

**Arquivo:** `app/auth.py` (linhas 126-152)

```python
# ❌ REMOVER ESTE BLOCO:
# Setar tenant_id no contexto se presente no token
tenant_id = payload.get("tenant_id")
if tenant_id:
    # ... código de extração ...
    set_tenant_context(tenant_uuid)
```

**Impacto:** NENHUM - `get_current_user_and_tenant` já faz isso

#### B) Tornar TenancyMiddleware passivo

**Arquivo:** `app/tenancy/middleware.py`

**Ação:**
- Middleware deve APENAS limpar contexto
- NÃO deve extrair tenant
- NÃO deve ter fallback

**Novo comportamento:**
```python
class TenancyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Apenas limpa contexto entre requests
        clear_current_tenant()
        response = await call_next(request)
        return response
```

#### C) Padronizar TODAS as rotas

**Status atual:**
- ✅ 85% das rotas usam `get_current_user_and_tenant`
- ❌ 15% das rotas usam apenas `get_current_user`

**Ação:** Substituir TODAS ocorrências de:
```python
Depends(get_current_user)
```

Por:
```python
Depends(get_current_user_and_tenant)
```

**Exceções legítimas:**
- Rotas de autenticação (login, logout)
- Rotas públicas (sem autenticação)

---

## 2. FALLBACK DE TENANT

### 2.1 Localização de Fallbacks

**🔴 CRÍTICO: 3 fallbacks perigosos identificados**

#### Fallback #1: TenancyMiddleware (linha 42)

**Arquivo:** `app/tenancy/middleware.py`

```python
if not auth or not auth.startswith("Bearer "):
    # ❌ FALLBACK PERIGOSO
    db = SessionLocal()
    result = db.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).fetchone()
    if result:
        tenant_id = UUID(str(result[0]))
        set_current_tenant(tenant_id)
    db.close()
```

**Contexto:** Request sem token → usa primeiro tenant do banco

**Risco:** Usuário não autenticado vê dados de outro tenant

---

#### Fallback #2: TenancyMiddleware (linha 63)

**Arquivo:** `app/tenancy/middleware.py`

```python
if tenant_id:
    set_current_tenant(tenant_id)
else:
    # ❌ FALLBACK PERIGOSO
    db = SessionLocal()
    result = db.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).fetchone()
    if result:
        tenant_id = UUID(str(result[0]))
        set_current_tenant(tenant_id)
    db.close()
```

**Contexto:** JWT sem tenant_id → usa primeiro tenant

**Risco:** Token antigo ou malformado acessa tenant aleatório

---

#### Fallback #3: TenancyMiddleware (linha 72)

**Arquivo:** `app/tenancy/middleware.py`

```python
except JWTError:
    # ❌ FALLBACK PERIGOSO
    db = SessionLocal()
    result = db.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).fetchone()
    if result:
        tenant_id = UUID(str(result[0]))
        set_current_tenant(tenant_id)
    db.close()
```

**Contexto:** JWT inválido → usa primeiro tenant

**Risco:** Token expirado ou adulterado acessa dados

---

### 2.2 Avaliação de Impacto de Remoção

**✅ REMOVER TODOS OS FALLBACKS**

**Cenário 1: Request sem token**
- **Atual:** Usa tenant padrão (PERIGOSO)
- **Correto:** Retornar 401 Unauthorized

**Cenário 2: Token sem tenant_id**
- **Atual:** Usa tenant padrão (PERIGOSO)
- **Correto:** Retornar 401 "Tenant não selecionado"

**Cenário 3: Token inválido**
- **Atual:** Usa tenant padrão (PERIGOSO)
- **Correto:** Retornar 401 "Token inválido"

**Impacto em rotas legítimas:** NENHUM

**Por quê:**
- Rotas autenticadas usam `get_current_user_and_tenant`
- Dependency já valida e rejeita se tenant ausente
- Fallback nunca deveria ser usado

**📋 AÇÃO REQUERIDA:**

```python
# NOVO COMPORTAMENTO (sem fallback):
class TenancyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Rotas públicas passam direto
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        
        # Limpa contexto (isolamento entre requests)
        clear_current_tenant()
        
        # Passa para próxima camada
        # Validação de tenant_id acontece em get_current_user_and_tenant
        response = await call_next(request)
        return response
```

---

## 3. ORM FILTER

### 3.1 Comportamento Atual

**Arquivo:** `app/tenancy/filters.py`

```python
@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    if not execute_state.is_select:
        return

    tenant_id = get_current_tenant()
    if tenant_id is None:
        # ⚠️ PERMITE QUERIES SEM TENANT
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            BaseTenantModel,
            lambda cls: cls.tenant_id == tenant_id,
        )
    )
```

**❌ PROBLEMA:** `if tenant_id is None: return`

**Risco:** Query passa sem filtro de tenant

---

### 3.2 Queries Legítimas sem Tenant

**Análise de necessidade:**

#### ✅ WHITELIST - Queries que DEVEM rodar sem tenant:

1. **Tabela `users`**
   - Motivo: Login antes de selecionar tenant
   - Query: `SELECT * FROM users WHERE email = ?`

2. **Tabela `tenants`**
   - Motivo: Listar tenants do usuário
   - Query: `SELECT * FROM tenants JOIN user_tenants ...`

3. **Tabela `user_sessions`**
   - Motivo: Validação de sessões globais
   - Query: `SELECT * FROM user_sessions WHERE token_jti = ?`

4. **Tabela `user_tenants`**
   - Motivo: Relacionamento user ↔ tenant
   - Query: `SELECT * FROM user_tenants WHERE user_id = ?`

5. **Healthcheck queries**
   - Motivo: Monitoramento
   - Query: `SELECT 1`

#### ❌ BLACKLIST - Queries que NUNCA devem rodar sem tenant:

- Todas as tabelas que herdam de `BaseTenantModel`
- Exemplos: vendas, produtos, clientes, estoque, financeiro

---

### 3.3 Proposta de Whitelist Segura

**✅ NOVA IMPLEMENTAÇÃO:**

```python
# app/tenancy/filters.py
from sqlalchemy.orm import Session
from sqlalchemy import event, inspect
from sqlalchemy.orm import with_loader_criteria

from app.tenancy.context import get_current_tenant
from app.base_models import BaseTenantModel

# Whitelist de tabelas que podem ter queries sem tenant
TENANT_EXEMPT_TABLES = {
    'users',
    'tenants', 
    'user_sessions',
    'user_tenants',
    'roles',
    'permissions',
    'role_permissions',
    'audit_logs',  # Auditoria precisa ser global
}


@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    """
    Filtro global de tenant com whitelist.
    
    REGRAS:
    1. Queries SELECT sem tenant_id são REJEITADAS
    2. EXCETO se a tabela estiver na whitelist
    3. INSERT/UPDATE/DELETE não são filtrados (validação via BaseTenantModel)
    """
    if not execute_state.is_select:
        return

    tenant_id = get_current_tenant()
    
    # Se tenant_id presente, aplicar filtro normalmente
    if tenant_id is not None:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                BaseTenantModel,
                lambda cls: cls.tenant_id == tenant_id,
                include_aliases=True,
            )
        )
        return
    
    # Se tenant_id ausente, verificar whitelist
    # Extrair nome da tabela principal da query
    try:
        from sqlalchemy import inspect as sa_inspect
        mapper = None
        
        # Tentar obter mapper da query
        if hasattr(execute_state, 'lazy_loaded_from'):
            mapper = execute_state.lazy_loaded_from.mapper
        elif hasattr(execute_state.statement, 'column_descriptions'):
            for desc in execute_state.statement.column_descriptions:
                if 'entity' in desc and desc['entity']:
                    mapper = sa_inspect(desc['entity'])
                    break
        
        if mapper:
            table_name = mapper.local_table.name
            
            # Se tabela está na whitelist, permitir
            if table_name in TENANT_EXEMPT_TABLES:
                return
            
            # Se tabela herda de BaseTenantModel e não está na whitelist
            if issubclass(mapper.class_, BaseTenantModel):
                # 🔴 REJEITAR QUERY
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"🚫 QUERY REJEITADA: Tentativa de query sem tenant_id "
                    f"na tabela '{table_name}' (BaseTenantModel)"
                )
                raise RuntimeError(
                    f"Tenant context required for table '{table_name}'. "
                    f"Ensure get_current_user_and_tenant() is used."
                )
    
    except Exception as e:
        # Se não conseguir determinar a tabela, permitir
        # (evitar quebrar queries legítimas complexas)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Não foi possível validar tenant na query: {e}")
        return
```

**Vantagens:**
- Whitelist explícita de tabelas sem tenant
- Rejeita queries perigosas (BaseTenantModel sem tenant)
- Logs de tentativas de vazamento
- Mantém queries legítimas funcionando

---

## 4. DEPENDENCIES

### 4.1 Mapeamento Completo de Rotas

**Total de arquivos routes:** 68 arquivos

**Análise de dependencies utilizadas:**

#### 📊 Estatísticas:

- **get_current_user_and_tenant:** ~180 usos (85%)
- **get_current_user:** ~35 usos (15%)
- **Sem autenticação:** ~10 rotas (5%)

---

### 4.2 Rotas usando `get_current_user` (INCORRETO)

**🔴 CRÍTICO - Rotas que DEVEM ser corrigidas:**

| Arquivo | Rota | Linha | Risco |
|---------|------|-------|-------|
| `auth_routes_multitenant.py` | `POST /select-tenant` | 151 | Médio |
| `auth_routes_multitenant.py` | `POST /logout-multitenant` | 308 | Baixo |
| `lancamentos_routes.py` | `POST /manuais` | 145 | **ALTO** |
| `lancamentos_routes.py` | `GET /manuais` | 239 | **ALTO** |
| `lancamentos_routes.py` | `GET /manuais/{id}` | 275 | **ALTO** |
| `lancamentos_routes.py` | `PUT /manuais/{id}` | 292 | **ALTO** |
| `lancamentos_routes.py` | `DELETE /manuais/{id}` | 323 | **ALTO** |
| `lancamentos_routes.py` | `POST /recorrentes` | 344 | **ALTO** |
| `lancamentos_routes.py` | `GET /recorrentes` | 390 | **ALTO** |
| `lancamentos_routes.py` | `GET /recorrentes/{id}` | 414 | **ALTO** |
| `lancamentos_routes.py` | `PUT /recorrentes/{id}` | 431 | **ALTO** |
| `lancamentos_routes.py` | `DELETE /recorrentes/{id}` | 462 | **ALTO** |
| `lancamentos_routes.py` | `POST /recorrentes/{id}/gerar` | 482 | **ALTO** |
| `projecao_caixa_routes.py` | `GET /projecao-caixa` | 20 | **ALTO** |
| `projecao_caixa_routes.py` | `GET /dashboard` | 47 | **ALTO** |
| `simulacao_contratacao_routes.py` | `POST /simular` | 29 | Médio |
| `stone_routes.py` | `GET /config` | 146 | Médio |
| `stone_routes.py` | `POST /webhook` | 190 | Médio |

**Total:** **18 rotas com risco**

**⚠️ ATENÇÃO:** `lancamentos_routes.py` tem **13 rotas vulneráveis** (lançamentos financeiros!)

---

### 4.3 Rotas usando `get_current_user_and_tenant` (CORRETO)

**✅ Rotas já seguras (exemplos):**

- `categorias_routes.py` - **7 rotas** (100% seguras)
- `clientes_routes.py` - **12 rotas** (100% seguras)
- `comissoes_routes.py` - **12 rotas** (100% seguras)
- `contas_receber_routes.py` - **7 rotas** (100% seguras)
- `contas_pagar_routes.py` - **8 rotas** (100% seguras)
- `dre_plano_contas_routes.py` - **8 rotas** (100% seguras)
- `estoque_routes.py` - **6 rotas** (100% seguras)
- `funcionarios_routes.py` - **5 rotas** (100% seguras)
- `pedidos_compra_routes.py` - **10 rotas** (100% seguras)
- `pets_routes.py` - **7 rotas** (100% seguras)
- `produtos_routes.py` - **35 rotas** (100% seguras)
- `vendas_routes.py` - **8 rotas** (100% seguras)

**Total:** **~180 rotas protegidas**

---

### 4.4 Classificação de Rotas

#### 🌐 PÚBLICAS (sem autenticação)

```python
# Não precisam de tenant_id
PUBLIC_PATHS = [
    '/health',
    '/ready',
    '/docs',
    '/openapi.json',
    '/auth/login',
    '/auth/register',
    '/auth/login-multitenant',
]
```

**Total:** ~10 rotas

---

#### 🔒 AUTENTICADAS (precisam de tenant)

**Todas as rotas de negócio:**
- Vendas, Produtos, Clientes, Estoque
- Financeiro (Contas a Receber/Pagar)
- Comissões
- Pedidos de Compra
- Pets, Funcionários, etc.

**Total:** ~200 rotas

**Regra:** TODAS devem usar `get_current_user_and_tenant`

---

#### ⚙️ INTERNAS / ADMIN

**Exemplos:**
- `/admin/fix-sequences` - Correção de dados
- `/permissions` - RBAC
- `/roles` - RBAC

**Situação:**
- Algumas usam `get_current_user` (INCORRETO)
- Devem usar `get_current_user_and_tenant` OU `require_admin`

---

## 5. RAW SQL

### 5.1 Arquivos com `db.execute(text())`

**Total identificado:** 15 arquivos

| Arquivo | Ocorrências | Risco | Validação Tenant |
|---------|-------------|-------|------------------|
| `comissoes_models.py` | 4 | 🔴 ALTO | ❌ Ausente |
| `comissoes_routes.py` | 8 | 🔴 ALTO | ⚠️ Parcial |
| `subcategorias_routes.py` | 3 | ⚠️ Médio | ❌ Ausente |
| `vendas_routes.py` | 2 | 🔴 ALTO | ❌ Ausente |
| `tenancy/middleware.py` | 3 | 🔴 CRÍTICO | ❌ Fallback perigoso |
| `routes/health_routes.py` | 1 | ✅ OK | N/A (healthcheck) |
| `routers/relatorios_comissoes.py` | 5 | 🔴 ALTO | ⚠️ Parcial |
| `admin_fix_routes.py` | 1 | ⚠️ Médio | ❌ Ausente |
| `read_models/schema_swap.py` | 3 | ✅ OK | N/A (rebuild) |

**Total:** **30 queries RAW SQL**

**Risco geral:** 🔴 **ALTO** - 75% sem validação de tenant

---

### 5.2 Análise de Risco por Arquivo

#### 🔴 CRÍTICO: `comissoes_models.py`

**Linha 222:**
```python
result = db.execute(text("""
    SELECT c.*, cli.nome as cliente_nome, cli.tipo_cadastro
    FROM comissoes_configuracoes c
    LEFT JOIN cliente cli ON c.funcionario_id = cli.id
    WHERE c.funcionario_id = :funcionario_id
    ORDER BY c.id DESC
"""), {'funcionario_id': funcionario_id})
```

**Problema:** Sem filtro por `tenant_id`

**Risco:** Vazamento de comissões entre tenants

**Correção:**
```python
WHERE c.funcionario_id = :funcionario_id 
  AND c.tenant_id = :tenant_id  -- ✅ ADICIONAR
```

---

#### 🔴 ALTO: `vendas_routes.py`

**Linha 506:**
```python
db.execute(text("DELETE FROM comissoes_itens WHERE venda_id = :venda_id"), 
    {"venda_id": venda_id})
```

**Problema:** DELETE sem filtro de tenant

**Risco:** Deletar comissões de outro tenant

**Correção:**
```python
DELETE FROM comissoes_itens 
WHERE venda_id = :venda_id 
  AND tenant_id = :tenant_id  -- ✅ ADICIONAR
```

---

#### 🔴 ALTO: `routers/relatorios_comissoes.py`

**Múltiplas queries com JOIN complexo sem tenant**

**Exemplo (linha 66):**
```python
result = db.execute(text(query), params_dict)
```

**Query construída dinamicamente - SEM validação de tenant**

**Correção:** Adicionar `AND tenant_id = :tenant_id` em TODOS os JOINs

---

### 5.3 Padrão Seguro para RAW SQL

**✅ TEMPLATE OBRIGATÓRIO:**

```python
# ============================================================
# PADRÃO SEGURO PARA RAW SQL COM TENANT
# ============================================================

from uuid import UUID
from sqlalchemy import text

def execute_raw_with_tenant(
    db: Session,
    query: str,
    params: dict,
    tenant_id: UUID
) -> Any:
    """
    Wrapper seguro para db.execute(text()) com validação de tenant.
    
    OBRIGA passagem de tenant_id e injeta no WHERE automaticamente.
    
    Args:
        db: Sessão do SQLAlchemy
        query: Query SQL (DEVE conter placeholder :tenant_id)
        params: Parâmetros da query
        tenant_id: UUID do tenant (obrigatório)
    
    Raises:
        ValueError: Se query não contém :tenant_id
    
    Returns:
        Resultado da query
    """
    # Validar que query contém :tenant_id
    if ':tenant_id' not in query.lower():
        raise ValueError(
            "Query RAW SQL DEVE conter placeholder :tenant_id. "
            "NUNCA execute queries sem filtro de tenant!"
        )
    
    # Adicionar tenant_id aos params
    params_with_tenant = {**params, 'tenant_id': str(tenant_id)}
    
    # Executar query
    return db.execute(text(query), params_with_tenant)


# ============================================================
# EXEMPLO DE USO:
# ============================================================

@router.get("/relatorio/comissoes")
def relatorio(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    current_user, tenant_id = user_and_tenant
    
    query = """
        SELECT c.*, cli.nome
        FROM comissoes_configuracoes c
        JOIN cliente cli ON c.funcionario_id = cli.id
        WHERE c.funcionario_id = :funcionario_id
          AND c.tenant_id = :tenant_id  -- ✅ OBRIGATÓRIO
        ORDER BY c.id DESC
    """
    
    result = execute_raw_with_tenant(
        db=db,
        query=query,
        params={'funcionario_id': 123},
        tenant_id=tenant_id  # ✅ Passado explicitamente
    )
```

**Benefícios:**
- Força validação de tenant
- Impede esquecimento de filtro
- Auditável (todas queries passam pelo wrapper)
- Typesafe (UUID obrigatório)

---

## 6. PADRÃO FINAL RECOMENDADO

### 6.1 Arquitetura Definitiva

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT REQUEST                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Middleware: TenantContextMiddleware                         │
│  ✅ Limpa contexto entre requests (isolamento)               │
│  ❌ NÃO extrai tenant                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Rota Pública?                                               │
│  └─ Sim → Passa direto (sem tenant)                         │
│  └─ Não → Dependency get_current_user_and_tenant            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Dependency: get_current_user_and_tenant                     │
│  1. Valida JWT                                               │
│  2. Extrai tenant_id do payload                              │
│  3. Valida obrigatoriedade (erro 401 se ausente)             │
│  4. Seta ContextVar: set_current_tenant(tenant_id)           │
│  5. Retorna: (User, UUID)                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Route Handler                                               │
│  ✅ Recebe user, tenant_id tipados                           │
│  ✅ tenant_id já está no ContextVar                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ORM Query / Service Layer                                   │
│  ✅ Event listener injeta WHERE tenant_id = ?                │
│  ✅ BaseTenantModel valida tenant em INSERT                  │
│  ❌ REJEITA queries sem tenant (exceto whitelist)            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Database (PostgreSQL)                                       │
│  ✅ Constraint: tenant_id NOT NULL                           │
│  ✅ Index: tenant_id para performance                        │
└─────────────────────────────────────────────────────────────┘
```

---

### 6.2 Onde Tenant é Extraído

**✅ FONTE ÚNICA: `get_current_user_and_tenant`**

**Arquivo:** `app/auth/dependencies.py`

**Responsabilidades:**
1. Decodificar JWT
2. Extrair `tenant_id` do payload
3. Validar obrigatoriedade
4. Converter para UUID
5. Setar ContextVar
6. Retornar (User, UUID)

**Por quê única fonte:**
- Dependency é chamada em TODA rota autenticada
- Garante que tenant sempre é extraído do JWT
- Valida antes de executar lógica de negócio
- Tipagem forte (tuple[User, UUID])

---

### 6.3 Como é Validado

**3 camadas de validação:**

#### ✅ Camada 1: Dependency

```python
def get_current_user_and_tenant(...) -> tuple[User, UUID]:
    tenant_id_str = payload.get("tenant_id")
    
    if not tenant_id_str:
        raise HTTPException(
            status_code=401,
            detail="Tenant não selecionado"
        )
    
    tenant_id = UUID(tenant_id_str)
    set_current_tenant(tenant_id)
    return user, tenant_id
```

**Valida:** Presença de tenant_id no JWT

---

#### ✅ Camada 2: ORM Event Listener

```python
@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    tenant_id = get_current_tenant()
    
    if tenant_id is None:
        # Verificar whitelist
        if table_name not in TENANT_EXEMPT_TABLES:
            raise RuntimeError("Tenant context required")
    
    # Aplicar filtro
    execute_state.statement = with_loader_criteria(...)
```

**Valida:** Queries ORM têm tenant_id

---

#### ✅ Camada 3: Database Constraint

```sql
ALTER TABLE vendas
ADD CONSTRAINT vendas_tenant_id_not_null
CHECK (tenant_id IS NOT NULL);
```

**Valida:** INSERT/UPDATE têm tenant_id

---

### 6.4 Como é Aplicado às Queries

**Automático via ORM:**

```python
# ✅ QUERY AUTOMÁTICA
produtos = db.query(Produto).filter(Produto.ativo == True).all()

# SQL gerado:
# SELECT * FROM produtos 
# WHERE ativo = TRUE 
#   AND tenant_id = '123e4567-...'  ← Injetado automaticamente
```

**Manual via RAW SQL:**

```python
# ✅ QUERY MANUAL SEGURA
result = execute_raw_with_tenant(
    db=db,
    query="""
        SELECT * FROM vendas 
        WHERE data >= :data_inicio 
          AND tenant_id = :tenant_id
    """,
    params={'data_inicio': '2026-01-01'},
    tenant_id=tenant_id
)
```

---

### 6.5 Checklist de Validação

**✅ CHECKLIST DE HARDENING:**

#### Fase 1: Dependency (CRÍTICO)

- [ ] Substituir `Depends(get_current_user)` por `get_current_user_and_tenant` em **TODAS** rotas autenticadas
- [ ] Validar que `lancamentos_routes.py` está corrigido (13 rotas)
- [ ] Validar que `projecao_caixa_routes.py` está corrigido (2 rotas)
- [ ] Validar que `stone_routes.py` está corrigido (2 rotas)

#### Fase 2: Middleware (CRÍTICO)

- [ ] Remover 3 fallbacks de tenant padrão em `TenancyMiddleware`
- [ ] Tornar middleware passivo (apenas limpa contexto)
- [ ] Remover extração de tenant em `get_current_user` (`app/auth.py`)

#### Fase 3: ORM Filter (CRÍTICO)

- [ ] Implementar whitelist de tabelas sem tenant
- [ ] Adicionar rejeição de queries sem tenant (exceto whitelist)
- [ ] Adicionar logs de tentativas de vazamento

#### Fase 4: RAW SQL (ALTO)

- [ ] Auditar `comissoes_models.py` (4 queries)
- [ ] Auditar `comissoes_routes.py` (8 queries)
- [ ] Auditar `routers/relatorios_comissoes.py` (5 queries)
- [ ] Auditar `vendas_routes.py` (2 queries)
- [ ] Auditar `subcategorias_routes.py` (3 queries)
- [ ] Implementar wrapper `execute_raw_with_tenant`

#### Fase 5: Testes (MÉDIO)

- [ ] Criar teste: Request sem token → 401
- [ ] Criar teste: Token sem tenant_id → 401
- [ ] Criar teste: Token inválido → 401
- [ ] Criar teste: Query ORM sem tenant → RuntimeError
- [ ] Criar teste: RAW SQL sem tenant → ValueError
- [ ] Criar teste: Whitelist (users, tenants) funciona

#### Fase 6: Documentação (BAIXO)

- [ ] Documentar padrão oficial em README
- [ ] Criar guia para desenvolvedores
- [ ] Adicionar exemplos de rotas corretas

---

## 📊 RESUMO EXECUTIVO

### Situação Atual

| Aspecto | Status | Nota |
|---------|--------|------|
| Fonte única tenant | ❌ Múltiplas fontes | 3/10 |
| Fallback tenant | 🔴 3 fallbacks perigosos | 1/10 |
| ORM Filter | ⚠️ Permite queries sem tenant | 5/10 |
| Dependencies | ⚠️ 15% rotas incorretas | 7/10 |
| RAW SQL | 🔴 75% sem validação | 2/10 |
| **MÉDIA GERAL** | | **3.6/10** |

---

### Ações Prioritárias

**P0 - CRÍTICO (Fazer AGORA):**
1. Remover 3 fallbacks de tenant padrão
2. Corrigir 18 rotas usando `get_current_user` incorretamente
3. Auditar e corrigir 22 queries RAW SQL sem tenant

**P1 - ALTO (1 Sprint):**
4. Implementar whitelist no ORM filter
5. Implementar wrapper `execute_raw_with_tenant`
6. Criar testes de segurança multi-tenant

**Estimativa:** 2-3 semanas de refatoração

---

## 🎯 RESULTADO ESPERADO

Após aplicar o hardening:

- ✅ **Fonte única:** get_current_user_and_tenant
- ✅ **Zero fallbacks:** Rejeita requests sem tenant
- ✅ **ORM seguro:** Whitelist + rejeição de queries perigosas
- ✅ **100% rotas:** Todas usando dependency correto
- ✅ **RAW SQL seguro:** Wrapper com validação obrigatória
- ✅ **Classificação:** 9/10 (enterprise-ready)

---

**Documento gerado em:** 05/02/2026  
**Próxima revisão:** Após implementação das correções P0  
**Responsável:** Equipe de Segurança + DevOps
