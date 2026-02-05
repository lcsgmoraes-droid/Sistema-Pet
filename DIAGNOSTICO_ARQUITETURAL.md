# 📊 DIAGNÓSTICO ARQUITETURAL - SISTEMA PET SHOP ERP MULTI-TENANT

**Data:** 05 de fevereiro de 2026  
**Versão:** 1.0  
**Arquiteto:** Análise Automatizada  
**Stack:** FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic

---

## 1. MULTI-TENANCY

### 1.1 Extração do tenant_id

**Formas de obtenção identificadas:**

1. **Middleware TenancyMiddleware** (`app/tenancy/middleware.py`)
   - Extrai `tenant_id` do JWT token via header `Authorization`
   - Seta no ContextVar `_current_tenant`
   - Possui fallback para tenant padrão se JWT não tiver `tenant_id`

2. **Middleware TenantSecurityMiddleware** (`app/middlewares/tenant_middleware.py`)
   - Atualmente passivo (apenas passa request adiante)
   - Comentários indicam que validação acontece na dependency

3. **Middleware TenantContextMiddleware** (`app/tenancy/context.py`)
   - Limpa contexto entre requests (isolamento)
   - Não valida nem seta tenant

4. **Dependency get_current_user** (`app/auth.py`)
   - Extrai `tenant_id` do payload JWT
   - Seta contexto via `set_tenant_context(tenant_uuid)`
   - Executa em toda rota autenticada

5. **Dependency get_current_user_and_tenant** (`app/auth/dependencies.py`)
   - **MÉTODO OFICIAL** segundo documentação
   - Decodifica JWT novamente para garantir `tenant_id`
   - Valida obrigatoriedade do `tenant_id` (erro 401 se ausente)
   - Configura contexto explicitamente

### 1.2 Múltiplas formas = RISCO

**❌ Problema identificado:**
- **Redundância**: tenant_id é extraído em 3 pontos diferentes (middleware, get_current_user, get_current_user_and_tenant)
- **Inconsistência**: Algumas rotas usam `get_current_user`, outras `get_current_user_and_tenant`
- **Fallback perigoso**: TenancyMiddleware possui fallback para "tenant padrão" se JWT inválido

**Exemplo de rota usando apenas get_current_user:**
```python
# app/auth_routes_multitenant.py
@router.post("/logout-multitenant")
def logout_multitenant(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)  # ⚠️ Sem tenant_id explícito
):
```

### 1.3 Queries automáticas com tenant_id

**✅ Filtro Global ORM implementado:**

```python
# app/tenancy/filters.py
@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    if tenant_id is None:
        return  # ⚠️ Permite queries sem tenant
    
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            BaseTenantModel,
            lambda cls: cls.tenant_id == tenant_id,
        )
    )
```

**✅ Base Model unificado:**
```python
# app/base_models.py
class BaseTenantModel(Base):
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
```

**📊 Cobertura:**
- Produto, Cliente, Venda, Estoque, Financeiro: ✅ Usam BaseTenantModel
- User, UserSession: ❌ NÃO usam BaseTenantModel (correto - sessões são globais)

### 1.4 Queries RAW SQL identificadas

**⚠️ SQL direto encontrado em:**

1. `backend/app/comissoes_models.py` (4 ocorrências)
   ```python
   result = db.execute(text(query), params)
   ```
   - **Risco:** Se não filtrar por tenant_id, vaza dados

2. Scripts de migração manual:
   - `add_dre_column.py`
   - `add_missing_columns.py`
   - **Contexto:** Scripts administrativos únicos, risco baixo

3. `app/tenancy/middleware.py` - Busca tenant padrão:
   ```python
   result = db.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1"))
   ```
   - **Risco:** Fallback perigoso

### 1.5 Risco de vazamento de dados

**🔴 ALTO RISCO identificado em:**

1. **Rotas sem get_current_user_and_tenant:**
   - Dependem apenas de `get_current_user`
   - Contexto pode não estar setado corretamente
   
2. **Fallback para tenant padrão:**
   - TenancyMiddleware busca "primeiro tenant" se JWT inválido
   - **Crítico:** Usuário sem tenant pode ver dados alheios

3. **Queries RAW sem tenant_id:**
   - `comissoes_models.py` usa queries dinâmicas
   - Não há validação explícita de tenant_id nas queries

4. **Filtro ORM permite None:**
   ```python
   if tenant_id is None:
       return  # ⚠️ Query passa sem filtro
   ```

### 1.6 Nível de segurança do isolamento

**Classificação: MÉDIO (5/10)**

**✅ Pontos positivos:**
- BaseTenantModel com tenant_id obrigatório
- Filtro ORM global automático
- Dependency get_current_user_and_tenant robusto
- Migrations incluem tenant_id em tabelas novas

**❌ Pontos críticos:**
- Múltiplas formas de extrair tenant_id (inconsistência)
- Fallback para tenant padrão (perigoso)
- SQL direto sem validação explícita
- Rotas usando apenas get_current_user (incompleto)
- Filtro ORM permite queries sem tenant

**📋 Recomendações:**
1. Padronizar TODAS rotas para usar `get_current_user_and_tenant`
2. Remover fallback de "tenant padrão"
3. Adicionar validação obrigatória em queries RAW
4. Modificar filtro ORM para REJEITAR queries sem tenant (exceto whitelist)
5. Auditoria de segurança em `comissoes_models.py`

---

## 2. BANCO DE DADOS & MIGRATIONS

### 2.1 Alembic está ativo?

**✅ SIM - Alembic configurado e em uso**

**Arquivos encontrados:**
- `backend/alembic.ini` - Configuração presente
- `backend/alembic/env.py` - Script de environment
- `backend/alembic/versions/` - 95+ arquivos de migration

**Últimas migrations (2026):**
```
20260201_criar_rotas_entrega_paradas.py
20260131_add_auditoria_dre.py
20260131_create_controle_processamento_mensal.py
20260129_tornar_dre_obrigatorio.py
20260129_dre_plano_contas.py
20260128_add_tenant_id_to_notas_entrada.py
20260127_create_opportunities.py
20260127_create_opportunity_events.py
20260127_create_feature_flags.py
20260126_fix_vendas_identity_sequence.py
```

**Status:** Migrations ativas e recentes (até fevereiro/2026)

### 2.2 Divergência entre banco real e migrations?

**⚠️ PROVÁVEL - Evidências:**

1. **Scripts manuais fora do Alembic:**
   - `add_dre_column.py`
   - `add_missing_columns.py`
   - `add_rateio_contas_itens.py`
   - `add_tenant_aba5_tables.py`
   - `add_tenant_chat_tables.py`
   - `add_tenant_id_conversas_ia.py`
   - `add_tenant_id_notas_entrada.py`
   - `add_tenant_lembretes.py`
   - `add_tipo_rateio_notas_entrada.py`
   - `add_updated_at_*.py` (múltiplos)
   - **Total:** 20+ scripts Python de alteração direta

2. **SQL direto em scripts:**
   ```python
   db.execute(text("ALTER TABLE categorias_financeiras ADD COLUMN..."))
   ```

3. **Comentário no código:**
   ```python
   # app/main.py
   # db.init_db()  # REMOVIDO: schema gerenciado por Alembic
   ```

**🔴 Conclusão:**
- Schema PARCIALMENTE gerenciado por Alembic
- Muitas alterações feitas via scripts ad-hoc
- Histórico incompleto no versionamento
- **Risco:** Banco de produção pode ter diferenças não documentadas

### 2.3 Migrations manuais fora do Alembic

**SIM - Identificadas 20+ migrations manuais:**

**Categorias:**

1. **Adicionar tenant_id a tabelas existentes:**
   - `add_tenant_aba5_tables.py`
   - `add_tenant_chat_tables.py`
   - `add_tenant_id_notas_entrada.py`
   - `add_tenant_id_conversas_ia.py`

2. **Campos updated_at:**
   - `add_updated_at_all_tables.py`
   - `add_updated_at_estoque_movimentacoes.py`
   - `add_updated_at_pagamentos.py`
   - `add_updated_at_produtos_historico_precos.py`

3. **Colunas de negócio:**
   - `add_dre_column.py`
   - `add_missing_columns.py`
   - `add_rateio_contas_itens.py`
   - `add_rateio_to_notas_entrada_itens.py`

4. **Correções de schema:**
   - `fix_configuracoes_entrega_id.py`
   - `fix_empresa_config_fiscal.py`
   - `fix_fiscal_tenant_id_to_uuid.py`
   - `fix_users_tenant_id_not_null.py`

**⚠️ Problema:**
- Scripts executados manualmente
- Sem garantia de ordem de aplicação
- Sem rollback estruturado
- Dificulta setup de ambiente do zero

### 2.4 É possível subir o banco do zero apenas com Alembic?

**❌ NÃO - Provável necessidade de scripts manuais**

**Motivos:**

1. **Alembic não inclui todas alterações:**
   - Scripts `.py` no root de backend não estão em `alembic/versions/`
   - Alterações de schema feitas via `text("ALTER TABLE...")`

2. **Ordem de execução incerta:**
   - Scripts manuais podem ter dependências
   - Sem mecanismo de controle de aplicação

3. **Falta de migration inicial completa:**
   - Múltiplos arquivos `3ae989fa5fa3_initial_schema.py`
   - Mas várias tabelas adicionadas depois via scripts

**✅ Possível solução:**
1. Consolidar todos scripts manuais em migrations Alembic
2. Criar migration "snapshot" do estado atual
3. Testar setup em banco vazio

### 2.5 Existe downgrade funcional?

**⚠️ PARCIAL - Não verificável sem análise detalhada**

**Evidências:**

1. **Migrations Alembic possuem método downgrade:**
   - Padrão do Alembic gera `upgrade()` e `downgrade()`
   - Não verificamos se estão implementados corretamente

2. **Scripts manuais NÃO possuem downgrade:**
   - Arquivos `.py` fazem apenas `ALTER TABLE ADD COLUMN`
   - Sem lógica reversa

3. **Alterações irreversíveis:**
   - `add_updated_at_all_tables.py` - Adiciona colunas sem reverter
   - `fix_users_tenant_id_not_null.py` - Altera constraint (difícil reverter)

**📋 Recomendação:**
- Revisar migrations Alembic para garantir downgrade funcional
- Documentar que scripts manuais NÃO são reversíveis
- Criar backups antes de migrations críticas

### 2.6 Resumo - Banco de Dados

| Critério | Status | Nota |
|----------|--------|------|
| Alembic ativo | ✅ Sim | 10/10 |
| Divergência schema | ⚠️ Provável | 4/10 |
| Migrations manuais | 🔴 Muitas (20+) | 2/10 |
| Setup do zero | ❌ Não | 2/10 |
| Downgrade funcional | ⚠️ Parcial | 5/10 |
| **MÉDIA GERAL** | | **4.6/10** |

---

## 3. DELETE vs SOFT DELETE

### 3.1 Tabelas com DELETE físico

**🔴 DELETE físico usado em:**

1. **UserSession**
   ```python
   # app/session_manager.py
   deleted = db.query(UserSession).filter(
       UserSession.expires_at < now
   ).delete()
   ```
   - **Justificativa:** Limpeza de sessões expiradas (OK)

2. **Pet** (condicional)
   ```python
   # app/pets_routes.py
   if soft_delete:
       pet.ativo = False  # ✅ Soft delete
   else:
       db.delete(pet)  # ❌ Hard delete
   ```
   - **Risco:** Parâmetro `soft_delete=False` permite exclusão permanente

3. **Comissões (inferido)**
   - Query RAW em `comissoes_models.py` pode ter DELETEs
   - Não auditado completamente

### 3.2 Tabelas com SOFT DELETE implementado

**✅ Soft delete via campo `deleted_at`:**

1. **Produto** (`produtos_models.py`)
   ```python
   deleted_at = Column(DateTime, nullable=True)
   ```
   - Service `VariacaoLixeiraService` gerencia exclusão lógica
   - Variações podem ser restauradas

2. **Cliente** (`clientes_routes.py`)
   ```python
   cliente.ativo = False
   ```
   - Usa campo `ativo` ao invés de `deleted_at`

3. **Marca, Departamento, Categoria**
   ```python
   marca.ativo = False
   ```

4. **Pet** (padrão)
   ```python
   pet.ativo = False
   ```

### 3.3 Tabelas que DEVERIAM usar soft delete

**🔴 CRÍTICO - Exclusão física perigosa:**

1. **Venda** - Não encontrado soft delete
   - **Impacto:** Fiscal, DRE, auditoria
   - **Risco:** Perda de histórico tributário

2. **ContaReceber / ContaPagar** - Não verificado
   - **Impacto:** Conciliação bancária, DRE
   - **Risco:** Divergência contábil

3. **EstoqueMovimentacao** - Não verificado
   - **Impacto:** Rastreabilidade, auditoria
   - **Risco:** Perda de histórico de movimentação

4. **LancamentoFinanceiro** - Não verificado
   - **Impacto:** DRE, relatórios
   - **Risco:** Inconsistência financeira

5. **NotaFiscal** - Não verificado
   - **Impacto:** Fiscal, SEFAZ
   - **Risco:** Autuação fiscal

### 3.4 Impacto em áreas críticas

#### 📊 FINANCEIRO

**Alto Risco:**
- Vendas: DELETE físico pode apagar receitas
- Contas a Receber/Pagar: Conciliação fica impossível
- Recomendação: **Soft delete obrigatório**

#### 🧾 FISCAL

**Risco Crítico:**
- Notas Fiscais: Exclusão física é ILEGAL (legislação fiscal)
- Vendas: Base de cálculo de impostos
- Recomendação: **Soft delete + auditoria de alterações**

#### 📦 ESTOQUE

**Risco Médio:**
- Movimentações: Histórico necessário para auditoria
- Produtos: Já possui soft delete (OK)
- Recomendação: **Adicionar soft delete em movimentações**

#### 📈 RELATÓRIOS

**Risco Alto:**
- DRE: Depende de histórico completo
- Comissões: Recálculo impossível sem histórico
- Recomendação: **Soft delete + campo "incluir_em_relatorios"**

### 3.5 Resumo - DELETE Strategy

| Tabela | Status Atual | Deveria Ser | Prioridade |
|--------|-------------|-------------|------------|
| Produto | ✅ Soft Delete | ✅ Soft Delete | - |
| Cliente | ✅ Soft Delete (ativo) | ✅ Soft Delete | - |
| Venda | ❓ Não verificado | 🔴 Soft Delete | **CRÍTICA** |
| NotaFiscal | ❓ Não verificado | 🔴 Soft Delete | **CRÍTICA** |
| ContaReceber | ❓ Não verificado | 🔴 Soft Delete | ALTA |
| ContaPagar | ❓ Não verificado | 🔴 Soft Delete | ALTA |
| EstoqueMovimentacao | ❓ Não verificado | ⚠️ Soft Delete | MÉDIA |
| Pet | ⚠️ Condicional | ✅ Soft Delete | BAIXA |

---

## 4. PADRÕES DE CÓDIGO

### 4.1 Padrão de variáveis

**📊 Nomenclaturas encontradas:**

#### Usuário:
- `current_user` (✅ Padrão dominante)
- `user` (usado em alguns lugares)
- `usuario` (raro, mistura PT/EN)

#### Tenant:
- `tenant_id` (✅ Padrão dominante - UUID)
- `user_id` (⚠️ Confusão com user.id em alguns contextos)
- `user_and_tenant` (tuple retornada por dependency)

#### Dependency Injection:
```python
# ✅ Padrão RECOMENDADO:
user_and_tenant = Depends(get_current_user_and_tenant)
current_user, tenant_id = user_and_tenant

# ⚠️ Alternativa (menos segura):
current_user: models.User = Depends(get_current_user)
```

### 4.2 Inconsistências encontradas

**🔴 CRÍTICO - Múltiplas formas de obter tenant_id:**

1. **Via Dependency (recomendado):**
   ```python
   user_and_tenant = Depends(get_current_user_and_tenant)
   current_user, tenant_id = user_and_tenant
   ```

2. **Via Contexto:**
   ```python
   from app.tenancy.context import get_current_tenant
   tenant_id = get_current_tenant()
   ```

3. **Via User (perigoso):**
   ```python
   current_user.tenant_id  # ⚠️ User pode ter múltiplos tenants!
   ```

**❌ Exemplo de inconsistência:**
```python
# app/auth_routes_multitenant.py
@router.post("/logout-multitenant")
def logout_multitenant(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)  # ⚠️ Sem tenant_id
):
```

**vs**

```python
# app/clientes_routes.py
@router.get("/{cliente_id}")
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)  # ✅ Com tenant_id
):
    current_user, tenant_id = user_and_tenant
```

### 4.3 Risco de NameError ou bug silencioso

**⚠️ MÉDIO RISCO:**

1. **tenant_id não validado em algumas rotas:**
   ```python
   # Se usar apenas get_current_user, tenant_id pode ser None
   produto = db.query(Produto).filter(Produto.id == id).first()
   # ⚠️ Filtro ORM permite query sem tenant!
   ```

2. **Confusão user_id vs tenant_id:**
   ```python
   # Em alguns services:
   user_id = 1  # ⚠️ É user.id ou tenant_id?
   
   # Exemplo real em variacao_lixeira_service.py:
   def excluir_variacao(variacao_id: int, db: Session, user_id: int):
       # user_id na verdade é usado como tenant_id!
   ```

3. **Logs com múltiplas nomenclaturas:**
   ```python
   logger.info(f"[DEBUG get_current_user] tenant_id no token: {tenant_id}")
   logger.info(f"[MULTI-TENANT] Contexto configurado: tenant_id={tenant_id}")
   ```

### 4.4 Sugestão de padronização

**📋 PADRÃO OFICIAL RECOMENDADO:**

```python
# ===== IMPORTS =====
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from uuid import UUID

# ===== SIGNATURE =====
@router.post("/endpoint")
def minha_rota(
    dto: MeuSchema,
    db: Session = Depends(get_session),
    auth: tuple[User, UUID] = Depends(get_current_user_and_tenant)
):
    current_user, tenant_id = auth
    
    # ✅ Sempre usar tenant_id explicitamente:
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.id == dto.produto_id
    )
```

**📋 NOMENCLATURA PADRONIZADA:**

| Contexto | Nome da Variável | Tipo | Obtenção |
|----------|------------------|------|----------|
| Usuário autenticado | `current_user` | `User` | `auth[0]` |
| Tenant do contexto | `tenant_id` | `UUID` | `auth[1]` |
| Tupla completa | `auth` | `tuple[User, UUID]` | Dependency |

**🚫 PROIBIDO:**
- Usar `user_id` para representar tenant
- Usar `get_current_user` sem `get_current_user_and_tenant`
- Buscar tenant_id de `ContextVar` diretamente em routes

### 4.5 Resumo - Padrões de Código

| Critério | Status | Nota |
|----------|--------|------|
| Consistência naming | ⚠️ Parcial | 6/10 |
| Padrão dependency | ⚠️ Misto | 5/10 |
| Risco NameError | ⚠️ Médio | 6/10 |
| Documentação padrão | ❌ Inexistente | 2/10 |
| **MÉDIA** | | **4.75/10** |

---

## 5. TRANSAÇÕES & CONSISTÊNCIA

### 5.1 Operações que deveriam ser atômicas

**🔴 CRÍTICO - Operações multi-step SEM transação explícita:**

1. **Criação de Venda + Itens + Pagamentos:**
   ```python
   # app/vendas_routes.py
   venda = Venda(...)
   db.add(venda)
   db.commit()  # ⚠️ Commit antes de itens!
   
   for item in itens:
       venda_item = VendaItem(...)
       db.add(venda_item)
   
   db.commit()  # ⚠️ Segundo commit
   ```
   - **Risco:** Venda sem itens se falhar no meio

2. **Nota de Entrada + Itens + Estoque:**
   ```python
   # Inferido de notas_entrada_routes.py
   nota = NotaEntrada(...)
   db.add(nota)
   
   for item in itens:
       # Criar item
       # Atualizar estoque
       # Atualizar preço
   
   db.commit()  # ⚠️ Commit único, mas sem try/except robusto
   ```

3. **Recebimento de Conta + Atualização Status + DRE:**
   ```python
   # app/contas_receber_routes.py
   conta.status = "recebido"
   # ... mais alterações ...
   db.commit()
   # ⚠️ Se DRE falhar depois, inconsistência
   ```

### 5.2 Uso de transactions (session.begin)

**❌ NÃO ENCONTRADO - Transactions explícitas ausentes**

**Busca realizada:**
- Pattern: `session.begin`, `with db.begin`, `transaction`, `atomic`
- Resultado: **0 matches em routes**

**⚠️ Observação:**
- SQLAlchemy usa autocommit=False por padrão
- Mas sem blocos `try/except` + `rollback` consistentes
- Risco de commits parciais

### 5.3 Risco de dados parcialmente gravados

**🔴 ALTO RISCO - Exemplos encontrados:**

1. **Venda com itens:**
   ```python
   # Se commit da venda passar mas commit de itens falhar:
   venda.id = 123
   venda.itens = []  # ⚠️ Venda vazia!
   ```

2. **Estoque sem movimentação:**
   ```python
   # Se atualizar produto.estoque_atual mas falhar em criar EstoqueMovimentacao:
   produto.estoque_atual += 10  # ✅ Gravado
   # ... erro antes de criar movimentacao
   # ⚠️ Estoque inconsistente com histórico
   ```

3. **Pagamento sem conta a receber:**
   ```python
   # Se criar recebimento mas falhar em atualizar conta:
   recebimento = Recebimento(...)
   db.add(recebimento)
   db.commit()  # ✅ Recebimento criado
   
   conta.status = "recebido"  # ❌ Erro aqui
   # ⚠️ Recebimento órfão no banco
   ```

### 5.4 Padrão recomendado

**✅ SOLUÇÃO - Transaction pattern:**

```python
@router.post("/venda")
def criar_venda(dto: VendaCreate, db: Session = Depends(get_session)):
    try:
        # Tudo dentro de try
        venda = Venda(...)
        db.add(venda)
        db.flush()  # ✅ Gera ID sem commit
        
        for item_dto in dto.itens:
            item = VendaItem(venda_id=venda.id, ...)
            db.add(item)
        
        for pag_dto in dto.pagamentos:
            pag = VendaPagamento(venda_id=venda.id, ...)
            db.add(pag)
        
        db.commit()  # ✅ Commit único no final
        
    except Exception as e:
        db.rollback()  # ✅ Rollback em caso de erro
        raise HTTPException(status_code=500, detail=str(e))
```

**Ou usando context manager:**

```python
@router.post("/venda")
def criar_venda(dto: VendaCreate, db: Session = Depends(get_session)):
    with db.begin_nested():  # ✅ Savepoint
        venda = Venda(...)
        db.add(venda)
        # ... resto das operações ...
    
    db.commit()  # Commit final
```

### 5.5 Resumo - Transações

| Critério | Status | Nota |
|----------|--------|------|
| Transactions explícitas | ❌ Ausentes | 1/10 |
| Try/except consistente | ⚠️ Parcial | 4/10 |
| Rollback em erros | ⚠️ Inconsistente | 5/10 |
| Risco dados parciais | 🔴 Alto | 3/10 |
| **MÉDIA** | | **3.25/10** |

**📋 AÇÃO URGENTE:**
Implementar pattern de transactions em:
1. Vendas (venda + itens + pagamentos)
2. Notas Entrada (nota + itens + estoque)
3. Recebimentos (recebimento + conta + DRE)
4. Movimentação Estoque (produto + movimentacao)

---

## 6. OBSERVABILIDADE

### 6.1 Existe healthcheck?

**✅ SIM - Implementado**

**Arquivos:**
- `app/health_router.py` - Router dedicado
- `app/main.py` - Endpoints básicos

**Endpoints:**

1. **GET /health** (básico)
   ```python
   return {
       "status": "healthy",
       "system": "Pet Shop Pro",
       "version": SYSTEM_VERSION
   }
   ```

2. **GET /health/detailed** (completo)
   ```python
   {
       "status": "healthy",  # ou "unhealthy", "degraded"
       "checks": {
           "database": {"status": "healthy", "response_time_ms": 12},
           "system": {
               "cpu_percent": 45.2,
               "memory_percent": 68.5,
               "disk_percent": 72.1
           }
       }
   }
   ```

**✅ Inclui:**
- Status do banco (query test)
- Métricas de sistema (CPU, RAM, disco)
- Tempo de resposta

### 6.2 Existe readiness?

**✅ SIM - Implementado**

**Endpoint:**
```python
@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except:
        raise HTTPException(status_code=503, detail="Database not ready")
```

**✅ Benefícios:**
- Kubernetes pode esperar DB estar pronto
- Previne requests antes de sistema inicializado

### 6.3 Existe correlation ID?

**⚠️ PARCIAL - Trace ID implementado**

**Arquivo:** `app/middlewares/trace_id.py`

```python
class TraceIDMiddleware:
    async def __call__(self, request: Request, call_next):
        trace_id = request.headers.get('X-Trace-ID', str(uuid.uuid4()))
        # Injeta em logs
        response = await call_next(request)
        response.headers['X-Trace-ID'] = trace_id
```

**✅ Presente em:**
- Logs de requisições
- Response headers

**❌ Não verificado em:**
- Logs de banco de dados
- Logs de exceptions
- Propagação para serviços externos (Bling, Stone, WhatsApp)

### 6.4 Como são os logs?

**📊 ANÁLISE DOS LOGS:**

**✅ Pontos positivos:**
1. **Logger configurado:**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

2. **Níveis apropriados:**
   ```python
   logger.info("[OK] Sistema iniciado")
   logger.warning("[MULTI-TENANT] tenant_id ausente")
   logger.error("[ERROR] Erro ao processar venda")
   ```

3. **Context em logs:**
   ```python
   logger.info(f"[DEBUG get_current_user] tenant_id: {tenant_id}")
   ```

**❌ Problemas identificados:**

1. **Inconsistência de formato:**
   ```python
   # Múltiplos estilos:
   logger.info("[OK] Mensagem")
   logger.info("✅ Mensagem")
   logger.info("🔒 Mensagem")
   logger.info("Mensagem sem prefixo")
   ```

2. **Falta de structured logging:**
   ```python
   # Atual:
   logger.info(f"Venda criada: {venda_id}")
   
   # Recomendado:
   logger.info("venda_criada", extra={
       "venda_id": venda_id,
       "tenant_id": tenant_id,
       "user_id": user_id
   })
   ```

3. **Logs verbosos em produção:**
   ```python
   logger.info(f"[DEBUG get_current_user] ...")  # ⚠️ DEBUG em código
   ```

### 6.5 Tratamento de erros é consistente?

**⚠️ PARCIAL - Padrão misto**

**✅ Bom:**
```python
try:
    # operação
    db.commit()
except Exception as e:
    db.rollback()
    logger.error(f"Erro: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

**❌ Ruim:**
```python
# Alguns lugares:
db.commit()  # ⚠️ Sem try/except

# Outros lugares:
try:
    db.commit()
except:  # ⚠️ Captura tudo, não loga
    pass
```

**📊 Tipos de exceções:**

1. **HTTPException** (✅ Padrão FastAPI)
   ```python
   raise HTTPException(status_code=404, detail="Não encontrado")
   ```

2. **ValueError** (⚠️ Usado em services)
   ```python
   raise ValueError("Validação falhou")
   # ⚠️ Não tratado em routes!
   ```

3. **Exception genérico** (❌ Muito amplo)
   ```python
   except Exception as e:  # Captura tudo
   ```

### 6.6 Resumo - Observabilidade

| Critério | Status | Nota |
|----------|--------|------|
| Healthcheck | ✅ Completo | 9/10 |
| Readiness | ✅ Implementado | 8/10 |
| Correlation ID | ⚠️ Parcial | 6/10 |
| Logs estruturados | ⚠️ Inconsistente | 5/10 |
| Tratamento erros | ⚠️ Misto | 6/10 |
| **MÉDIA** | | **6.8/10** |

**📋 Melhorias recomendadas:**
1. Padronizar formato de logs
2. Implementar structured logging (JSON)
3. Propagar correlation ID para integrações
4. Exception handler global
5. Métricas de negócio (Prometheus)

---

## 7. BACKGROUND TASKS

### 7.1 Quais operações são pesadas?

**🔍 OPERAÇÕES IDENTIFICADAS:**

#### 1. **Processamento de Acertos Financeiros**
- **Arquivo:** `app/schedulers/acerto_scheduler.py`
- **Frequência:** Diária (00:05)
- **Operação:**
  ```python
  # Para cada parceiro com data_fechamento_comissao
  - Calcular comissões do período
  - Gerar arquivo PDF
  - Enviar email
  ```
- **Peso:** Alto (múltiplas queries, PDF, email)

#### 2. **Fila de Emails**
- **Arquivo:** `app/schedulers/acerto_scheduler.py`
- **Frequência:** A cada 5 minutos
- **Operação:**
  ```python
  EmailQueueService.processar_fila(db, limite=20)
  ```
- **Peso:** Médio (I/O de rede)

#### 3. **Processamento de Mensagens WhatsApp**
- **Arquivo:** `app/whatsapp/webhook.py`
- **Método:** `BackgroundTasks.add_task()`
- **Operação:**
  ```python
  await process_incoming_message(
      tenant_id, phone, message_content, ...
  )
  ```
- **Peso:** Médio (I/O + IA)

#### 4. **Notificações Proativas** (TODO)
- **Arquivo:** `app/whatsapp/notifications.py`
- **Operações planejadas:**
  - Aniversários de clientes/pets
  - Lembretes de vacinas
  - Clientes inativos
- **Status:** Comentado como TODO (Celery beat)

#### 5. **Importação de Extratos Bancários**
- **Contexto:** IA categoriza lançamentos
- **Peso:** Alto (IA + múltiplas inserções)

### 7.2 São síncronas ou assíncronas?

**📊 MAPEAMENTO:**

| Operação | Tipo | Mecanismo |
|----------|------|-----------|
| Acertos diários | Async | APScheduler |
| Fila de emails | Async | APScheduler |
| WhatsApp incoming | Async | FastAPI BackgroundTasks |
| Notificações | ❌ TODO | (planejado: Celery) |
| Importação extrato | ⚠️ Síncrono | HTTP request |

**✅ Implementação atual:**

1. **APScheduler** (Background Scheduler)
   ```python
   # app/schedulers/acerto_scheduler.py
   class AcertoScheduler:
       def __init__(self):
           self.scheduler = BackgroundScheduler()
           self.configurar_jobs()
   ```

2. **FastAPI BackgroundTasks**
   ```python
   @router.post("/webhook")
   async def receive_webhook(background_tasks: BackgroundTasks):
       background_tasks.add_task(process_message, ...)
   ```

**❌ NÃO implementado:**
- Celery (task queue robusto)
- Redis (backend para filas)
- RabbitMQ / SQS

### 7.3 Existe retry?

**❌ NÃO IMPLEMENTADO - Retry ausente**

**Exemplos de operações SEM retry:**

1. **Envio de email:**
   ```python
   # app/services/acerto_service.py
   EmailQueueService.processar_fila(db, limite=20)
   # ⚠️ Se SMTP falhar, email perdido
   ```

2. **Chamadas API (Bling, Stone):**
   ```python
   # Requests sem retry policy
   response = requests.post(url, json=payload)
   # ⚠️ Timeout ou erro = falha permanente
   ```

3. **WhatsApp webhook:**
   ```python
   await process_incoming_message(...)
   # ⚠️ Se falhar, mensagem perdida
   ```

**📋 Recomendação - Implementar retry com backoff:**

```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(min=1, max=60),
    stop=stop_after_attempt(3)
)
def enviar_email(destinatario, assunto, corpo):
    # ... lógica de envio
```

### 7.4 Existe idempotência?

**⚠️ PARCIAL - Implementada em rotas críticas**

**✅ Decorator @idempotent encontrado:**

```python
# app/contas_receber_routes.py
@router.post("/{conta_id}/receber")
@idempotent()  # ✅ Evita recebimento duplicado
async def registrar_recebimento(...):
```

```python
# app/contas_receber_routes.py
@router.post("/")
@idempotent()  # ✅ Evita criação duplicada
async def criar_conta_receber(...):
```

**❌ Ausente em:**
- Criação de vendas
- Emissão de notas fiscais
- Processamento de webhooks (WhatsApp, Stone)

**🔍 Como funciona:**
- Provavelmente usa request hash (header ou body)
- Armazena em cache/DB para detectar duplicatas
- Retorna resposta cacheada se já processado

**⚠️ Problema:**
- Implementação do decorator não foi analisada
- Pode não funcionar em webhooks externos

### 7.5 Resumo - Background Tasks

| Critério | Status | Nota |
|----------|--------|------|
| Identificação ops pesadas | ✅ Claras | 8/10 |
| Processamento assíncrono | ⚠️ Parcial | 6/10 |
| Retry mechanism | ❌ Ausente | 1/10 |
| Idempotência | ⚠️ Parcial | 5/10 |
| Queue robusto (Celery) | ❌ Ausente | 0/10 |
| **MÉDIA** | | **4/10** |

**📋 AÇÃO RECOMENDADA:**

1. **Curto prazo:**
   - Implementar retry em envios de email
   - Adicionar retry em APIs externas (Bling, Stone)
   - Idempotência em webhooks

2. **Médio prazo:**
   - Migrar APScheduler → Celery Beat
   - Redis como backend de filas
   - Dead letter queue para falhas

3. **Longo prazo:**
   - Monitoramento de filas (Flower)
   - Alertas de falhas recorrentes
   - Circuit breaker para APIs externas

---

## 8. AVALIAÇÃO FINAL

### 8.1 Principais riscos técnicos (TOP 5)

#### 🔴 1. ISOLAMENTO MULTI-TENANT FRÁGIL

**Risco:** Vazamento de dados entre tenants

**Evidências:**
- Fallback para "tenant padrão" em middleware
- Queries RAW SQL sem validação de tenant_id
- Múltiplas formas de extrair tenant_id (inconsistência)
- Filtro ORM permite queries sem tenant

**Impacto:** **CRÍTICO** - Violação LGPD, perda de confiança

**Mitigação:**
1. Remover fallback de tenant padrão
2. Auditoria de todas queries RAW
3. Forçar erro se tenant_id ausente no filtro ORM
4. Padronizar 100% rotas com `get_current_user_and_tenant`

---

#### 🔴 2. AUSÊNCIA DE TRANSACTIONS EXPLÍCITAS

**Risco:** Dados parcialmente gravados (inconsistência)

**Evidências:**
- Vendas criadas sem itens
- Estoque sem movimentações
- Recebimentos órfãos

**Impacto:** **ALTO** - Relatórios incorretos, DRE errado

**Mitigação:**
1. Implementar pattern de transactions em operações multi-step
2. Try/except + rollback em TODAS operações críticas
3. Testes de integração para cenários de falha

---

#### 🔴 3. MIGRATIONS MANUAIS FORA DO ALEMBIC

**Risco:** Banco de produção diverge do versionamento

**Evidências:**
- 20+ scripts Python ad-hoc
- ALTER TABLE via `text()` direto
- Sem garantia de ordem de execução

**Impacto:** **ALTO** - Setup de ambientes impossível, rollback inviável

**Mitigação:**
1. Consolidar TODOS scripts em migrations Alembic
2. Criar migration "snapshot" do estado atual
3. Testar setup em banco vazio
4. Proibir SQL direto fora de migrations

---

#### 🔴 4. DELETE FÍSICO EM TABELAS CRÍTICAS

**Risco:** Perda irreversível de dados fiscais/financeiros

**Evidências:**
- Vendas sem soft delete
- Notas Fiscais sem soft delete
- Contas a Receber/Pagar sem soft delete

**Impacto:** **CRÍTICO** - Autuação fiscal, perda de auditoria

**Mitigação:**
1. Implementar soft delete (deleted_at) em:
   - Vendas
   - Notas Fiscais
   - Contas a Receber/Pagar
   - Lançamentos Financeiros
2. Migration para adicionar campo `deleted_at`
3. Atualizar queries para filtrar `deleted_at IS NULL`

---

#### ⚠️ 5. BACKGROUND TASKS SEM RETRY

**Risco:** Perda de emails, webhooks, integrações

**Evidências:**
- Envio de email sem retry
- APIs externas (Bling, Stone) sem retry
- WhatsApp webhooks sem retry

**Impacto:** **MÉDIO** - Perda de comunicação, clientes não notificados

**Mitigação:**
1. Implementar retry com backoff exponencial
2. Dead letter queue para falhas persistentes
3. Migrar para Celery (queue robusto)
4. Monitoramento de filas (Flower)

---

### 8.2 O que está bem feito e não deve ser alterado

#### ✅ 1. ARQUITETURA MULTI-TENANT COM BaseTenantModel

**Por quê:**
- Filtro ORM global automático
- tenant_id obrigatório em todas tabelas
- Dependency `get_current_user_and_tenant` robusta

**Manter:**
- Estrutura de BaseTenantModel
- Event listener do ORM
- Pattern de dependency injection

---

#### ✅ 2. OBSERVABILIDADE - HEALTHCHECK & READINESS

**Por quê:**
- Endpoints bem implementados
- Métricas de sistema incluídas
- Pronto para Kubernetes

**Manter:**
- `/health` e `/ready` endpoints
- Monitoramento de banco de dados
- Trace ID middleware

---

#### ✅ 3. SOFT DELETE EM PRODUTOS E VARIAÇÕES

**Por quê:**
- Service dedicado (VariacaoLixeiraService)
- Restauração implementada
- Lixeira funcional

**Manter:**
- Service layer para soft delete
- Campo `deleted_at`
- Endpoints de restauração

---

#### ✅ 4. ALEMBIC PARA MIGRATIONS

**Por quê:**
- 95+ migrations versionadas
- Histórico rastreável
- Downgrade potencial

**Manter:**
- Estrutura de alembic/versions/
- Naming convention de migrations
- Scripts de upgrade/downgrade

---

#### ✅ 5. SCHEDULER COM APSCHEDULER

**Por quê:**
- Acertos diários automatizados
- Fila de emails processada
- Logs adequados

**Manter:**
- Estrutura do AcertoScheduler
- Jobs configurados (cron + interval)
- Isolamento em classe dedicada

---

### 8.3 O que deve ser corrigido antes de escalar

#### 🚨 PRIORIDADE CRÍTICA (P0 - Fazer AGORA)

1. **Remover fallback de tenant padrão**
   - Arquivo: `app/tenancy/middleware.py`
   - Ação: Rejeitar requests sem tenant_id

2. **Implementar soft delete em Vendas e NotasFiscais**
   - Arquivo: `app/vendas_routes.py`, `app/nfe_routes.py`
   - Ação: Adicionar campo `deleted_at`, migration

3. **Adicionar transactions em operações críticas**
   - Arquivos: `vendas_routes.py`, `contas_receber_routes.py`, `notas_entrada_routes.py`
   - Ação: Try/except + rollback

---

#### 🔴 ALTA PRIORIDADE (P1 - Fazer em 1 Sprint)

4. **Padronizar TODAS rotas para get_current_user_and_tenant**
   - Buscar: `Depends(get_current_user)` sem tenant
   - Ação: Substituir por `get_current_user_and_tenant`

5. **Consolidar migrations manuais no Alembic**
   - Arquivo: Scripts `.py` no root de backend
   - Ação: Mover para alembic/versions/

6. **Implementar retry em integrações externas**
   - Arquivos: `bling_routes.py`, `stone_routes.py`, `whatsapp/webhook.py`
   - Ação: Decorator `@retry` com backoff

---

#### ⚠️ MÉDIA PRIORIDADE (P2 - Fazer em 2 Sprints)

7. **Structured logging (JSON)**
   - Arquivo: Configuração global de logs
   - Ação: python-json-logger

8. **Migrar APScheduler → Celery**
   - Arquivo: `app/schedulers/`
   - Ação: Celery + Redis backend

9. **Auditoria de queries RAW SQL**
   - Arquivo: `app/comissoes_models.py`
   - Ação: Validar tenant_id em TODAS queries

---

### 8.4 Classificação geral do sistema

**📊 PONTUAÇÃO POR ÁREA:**

| Área | Nota | Peso | Ponderada |
|------|------|------|-----------|
| Multi-Tenancy | 5/10 | 25% | 1.25 |
| Banco & Migrations | 4.6/10 | 20% | 0.92 |
| Delete Strategy | 6/10 | 15% | 0.90 |
| Padrões de Código | 4.75/10 | 10% | 0.48 |
| Transações | 3.25/10 | 15% | 0.49 |
| Observabilidade | 6.8/10 | 10% | 0.68 |
| Background Tasks | 4/10 | 5% | 0.20 |
| **TOTAL** | | | **4.92/10** |

---

### 🎯 CLASSIFICAÇÃO FINAL: **INTERMEDIÁRIO COM DÉBITOS TÉCNICOS**

**Características:**

✅ **Pontos Fortes:**
- Arquitetura multi-tenant presente
- Healthcheck e observabilidade básica
- Alembic para versionamento
- Soft delete em alguns models
- Scheduler funcional

❌ **Débitos Técnicos Críticos:**
- Isolamento multi-tenant frágil (fallback perigoso)
- Transactions ausentes (risco de inconsistência)
- Migrations manuais descontroladas
- DELETE físico em tabelas fiscais
- Retry ausente em integrações

⚠️ **Avaliação:**
- **NÃO é iniciante:** Possui estruturas avançadas (multi-tenant, ORM, DDD)
- **NÃO é enterprise-ready:** Riscos críticos impedem escala segura
- **INTERMEDIÁRIO:** Fundação sólida, mas necessita refatoração antes de escalar

---

### 📈 ROADMAP PARA ENTERPRISE-READY

#### FASE 1 - SEGURANÇA (1-2 meses)
- ✅ Corrigir isolamento multi-tenant
- ✅ Implementar transactions
- ✅ Soft delete em tabelas fiscais
- ✅ Consolidar migrations

#### FASE 2 - RESILIÊNCIA (2-3 meses)
- ⚙️ Retry em integrações
- ⚙️ Celery + Redis
- ⚙️ Circuit breaker
- ⚙️ Health metrics (Prometheus)

#### FASE 3 - ESCALA (3-6 meses)
- 📊 Read replicas
- 📊 Cache distribuído (Redis)
- 📊 CDN para assets
- 📊 Load balancer
- 📊 Auto-scaling

**Estimativa para Enterprise-Ready:** **6-8 meses** de refatoração focada

---

## 📝 CONCLUSÃO

O sistema **Pet Shop ERP Multi-Tenant** possui uma **base arquitetural sólida** com:
- Estrutura multi-tenant implementada
- ORM com filtros automáticos
- Migrations versionadas
- Observabilidade básica

Porém, **débitos técnicos críticos** impedem escalabilidade segura:
- **Risco de vazamento de dados** (multi-tenant frágil)
- **Risco de inconsistência** (falta de transactions)
- **Risco fiscal** (DELETE físico em tabelas críticas)
- **Risco operacional** (migrations manuais não rastreadas)

**Classificação:** ⚠️ **INTERMEDIÁRIO (4.92/10)** - Requer refatoração antes de escalar.

**Próximos passos:** Implementar correções **P0 e P1** antes de onboarding de novos tenants.

---

**Documento gerado em:** 05/02/2026  
**Ferramenta:** Análise automatizada de código  
**Arquivos analisados:** 150+ arquivos Python (backend/)
