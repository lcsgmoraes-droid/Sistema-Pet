# 🧬 BLUEPRINT OFICIAL DE BACKEND

> **Sistema Enterprise-Grade desde o primeiro commit**

Este documento define o padrão de qualidade obrigatório para **TODOS** os módulos do backend.

Não é opcional. Não é "boas práticas". É estrutura forçada.

---

## 📐 OS 4 PILARES OBRIGATÓRIOS

Todo módulo novo nasce com:

### 1. 🎯 **Funcional**
- Endpoint responde corretamente
- Retorna dados esperados
- HTTP status codes corretos

### 2. 💪 **Resiliente**  
- Não quebra com erro interno
- Suporta múltiplas requisições simultâneas
- Lida com unicode e caracteres especiais
- Resiste a parâmetros extremos

### 3. 🔒 **Seguro**
- JWT obrigatório
- Isolamento de tenant validado
- SQL injection bloqueado
- XSS sanitizado
- Rate limiting aplicado
- Erros sanitizados em produção

### 4. 📜 **Contrato Estável**
- Schema Pydantic validado
- Tipos corretos
- Campos obrigatórios presentes
- Formatos ISO 8601 para datas

---

## 🧪 ESTRUTURA OBRIGATÓRIA DE TESTES

```python
# tests/test_<modulo>_routes.py

# ============================================================================
# FUNCIONAL - Casos normais de uso
# ============================================================================

def test_listar_<recurso>(client, override_auth):
    """GET /<recurso> retorna lista de recursos"""
    pass

def test_buscar_<recurso>_por_id(client, override_auth):
    """GET /<recurso>/{id} retorna recurso específico"""
    pass

def test_criar_<recurso>(client, override_auth):
    """POST /<recurso> cria novo recurso"""
    pass

def test_atualizar_<recurso>(client, override_auth):
    """PUT /<recurso>/{id} atualiza recurso"""
    pass

def test_deletar_<recurso>(client, override_auth):
    """DELETE /<recurso>/{id} remove recurso"""
    pass


# ============================================================================
# RESILIENTE - Erros e situações extremas
# ============================================================================

def test_<recurso>_internal_error(client, override_auth):
    """Erro interno não quebra endpoint"""
    pass

def test_<recurso>_concurrent_requests(client, override_auth):
    """Múltiplas requisições simultâneas"""
    pass

def test_<recurso>_unicode_characters(client, override_auth):
    """Unicode e caracteres especiais"""
    pass

def test_<recurso>_extreme_parameters(client, override_auth):
    """Parâmetros extremos (números grandes, strings longas)"""
    pass


# ============================================================================
# SEGURO - Autenticação e ataques
# ============================================================================

def test_<recurso>_token_expirado_retorna_401(client, override_db):
    """Token expirado é rejeitado"""
    pass

def test_<recurso>_token_invalido_retorna_401(client, override_db):
    """Token inválido é rejeitado"""
    pass

def test_<recurso>_sql_injection_bloqueado(client, override_auth):
    """SQL injection é sanitizado"""
    pass

def test_<recurso>_xss_payload_bloqueado(client, override_auth):
    """XSS é sanitizado"""
    pass

def test_<recurso>_isolamento_tenant(client, override_db):
    """Tenants não vazam dados"""
    pass

def test_<recurso>_rate_limiting(client, override_auth):
    """Rate limiting protege contra abuso"""
    pass


# ============================================================================
# CONTRATO - Validação de schema
# ============================================================================

def test_contrato_<recurso>_schema(client, override_auth):
    """Response valida schema Pydantic"""
    from tests.helpers import assert_contract, assert_date_format, assert_non_negative
    
    response = client.get("/<recurso>")
    data = response.json()
    
    # Campos obrigatórios
    assert_contract(data, ["id", "nome", "data", "total"])
    
    # Tipos corretos
    assert isinstance(data["id"], int)
    assert isinstance(data["nome"], str)
    
    # Formatos
    assert_date_format(data["data"])
    assert_non_negative(data["total"])
```

---

## 🛠️ USANDO OS HELPERS

```python
from tests.helpers import (
    # Auth
    create_auth_header,
    create_expired_token,
    create_invalid_token,
    
    # Tenant
    get_default_tenant_id,
    assert_tenant_isolation,
    
    # Contratos
    assert_contract,
    assert_date_format,
    assert_non_negative,
    
    # Erros
    assert_401,
    assert_429,
    assert_500_production
)

# Exemplo: Teste de autenticação
def test_endpoint_requer_auth(client, override_db):
    headers = create_auth_header(user_id=1)
    response = client.get("/api/vendas", headers=headers)
    assert response.status_code == 200

# Exemplo: Teste de token expirado
def test_token_expirado(client, override_db):
    token = create_expired_token()
    response = client.get(
        "/api/vendas",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert_401(response)

# Exemplo: Teste de contrato
def test_contrato_venda(client, override_auth):
    response = client.get("/api/vendas/123")
    data = response.json()
    
    assert_contract(data, ["id", "cliente_nome", "total", "data"])
    assert_date_format(data["data"])
    assert_non_negative(data["total"], "total")

# Exemplo: Teste de isolamento de tenant
def test_isolamento_tenant(client, override_db):
    from tests.helpers import create_token_for_different_tenant
    
    # Tenant 1
    headers1 = create_auth_header(tenant_id=get_default_tenant_id())
    response1 = client.get("/api/vendas", headers=headers1).json()
    
    # Tenant 2
    token2 = create_token_for_different_tenant("99999999-9999-9999-9999-999999999999")
    headers2 = {"Authorization": f"Bearer {token2}"}
    response2 = client.get("/api/vendas", headers=headers2).json()
    
    # Validar que não há vazamento
    assert_tenant_isolation(response1, response2)
```

---

## 🏗️ ESTRUTURA DE MÓDULO COMPLETO

```
backend/app/<modulo>/
├── __init__.py
├── models.py          # Modelos SQLAlchemy
├── schemas.py         # Schemas Pydantic (request/response)
├── routes.py          # Endpoints FastAPI
├── service.py         # Lógica de negócio
└── queries.py         # Queries SQL (opcional)

backend/tests/
├── test_<modulo>_routes.py    # Testes completos (4 pilares)
└── helpers/                    # Biblioteca reutilizável
    ├── __init__.py
    ├── auth.py
    ├── tenant.py
    ├── contracts.py
    └── errors.py
```

---

## 🔒 MIDDLEWARES GLOBAIS (Já ativos)

Todo endpoint **automaticamente** passa por:

1. **RequestContextMiddleware** - Rastreamento e contexto
2. **SecurityAuditMiddleware** - Detecção de ataques
3. **RequestLoggingMiddleware** - Log estruturado
4. **RateLimitMiddleware** - Proteção contra abuso
   - Auth routes: 5 req/min
   - API routes: 100 req/min
5. **TenancyMiddleware** - Isolamento de tenants

**Ordem dos middlewares (já configurada):**
```python
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityAuditMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenancyMiddleware)
```

---

## 📋 CHECKLIST PARA NOVO MÓDULO

Antes de abrir PR:

- [ ] **Funcional:** 5+ testes de casos normais
- [ ] **Resiliente:** 4+ testes de erros/extremos
- [ ] **Seguro:** 6+ testes de auth/ataques
- [ ] **Contrato:** 1+ teste de schema
- [ ] **Mínimo:** 16 testes PASSANDO
- [ ] **Helpers:** Usa `tests/helpers` (não reinventa roda)
- [ ] **Schemas Pydantic:** Request/Response definidos
- [ ] **JWT:** Usa `Depends(get_current_user)`
- [ ] **Tenant:** Usa `get_tenant_context()`
- [ ] **Documentação:** Docstrings em endpoints

---

## 🚀 EXEMPLO COMPLETO: Módulo Produtos

```python
# app/produtos/routes.py
from fastapi import APIRouter, Depends
from app.auth.jwt import get_current_user
from app.tenancy.context import get_tenant_context
from .schemas import ProdutoCreate, ProdutoResponse
from .service import ProdutoService

router = APIRouter(prefix="/produtos", tags=["Produtos"])

@router.get("", response_model=list[ProdutoResponse])
def listar_produtos(
    current_user = Depends(get_current_user),
    tenant_context = Depends(get_tenant_context)
):
    """Lista produtos do tenant atual"""
    return ProdutoService.listar(tenant_context.tenant_id)

@router.post("", response_model=ProdutoResponse, status_code=201)
def criar_produto(
    produto: ProdutoCreate,
    current_user = Depends(get_current_user),
    tenant_context = Depends(get_tenant_context)
):
    """Cria novo produto"""
    return ProdutoService.criar(produto, tenant_context.tenant_id)
```

```python
# tests/test_produtos_routes.py
from tests.helpers import (
    create_auth_header,
    create_expired_token,
    assert_contract,
    assert_401,
    assert_tenant_isolation
)

# FUNCIONAL
def test_listar_produtos(client, override_auth):
    headers = create_auth_header()
    response = client.get("/produtos", headers=headers)
    assert response.status_code == 200

# RESILIENTE
def test_produtos_internal_error(client, override_auth):
    with patch("app.produtos.service.ProdutoService.listar", side_effect=Exception("DB error")):
        response = client.get("/produtos", headers=create_auth_header())
        assert response.status_code == 500

# SEGURO
def test_produtos_token_expirado(client, override_db):
    token = create_expired_token()
    response = client.get("/produtos", headers={"Authorization": f"Bearer {token}"})
    assert_401(response)

def test_produtos_isolamento_tenant(client, override_db):
    headers1 = create_auth_header(tenant_id="tenant-1")
    response1 = client.get("/produtos", headers=headers1).json()
    
    headers2 = create_auth_header(tenant_id="tenant-2")
    response2 = client.get("/produtos", headers=headers2).json()
    
    assert_tenant_isolation(response1, response2)

# CONTRATO
def test_contrato_produto_schema(client, override_auth):
    response = client.get("/produtos", headers=create_auth_header())
    data = response.json()
    
    assert isinstance(data, list)
    if len(data) > 0:
        assert_contract(data[0], ["id", "nome", "preco", "categoria"])
```

---

## 🎯 MÉTRICAS DE SUCESSO

### Cobertura Mínima
- **Funcional:** 80%+ de cobertura de código
- **Resiliente:** 100% de endpoints testados para erros
- **Seguro:** 100% de endpoints testados para auth
- **Contrato:** 100% de schemas validados

### Performance
- **Response time:** < 200ms (p95)
- **Rate limit:** Nenhum usuário legítimo bloqueado
- **Erros 500:** < 0.1% das requisições

### Segurança
- **SQL Injection:** 0 vulnerabilidades
- **XSS:** 0 vulnerabilidades
- **Tenant Leak:** 0 vazamentos
- **Auth Bypass:** 0 falhas

---

## 🔄 INTEGRAÇÃO CONTÍNUA

Pipeline valida automaticamente:

```yaml
# .github/workflows/backend-ci.yml
- run: pytest tests/ --cov=app --cov-report=term --cov-fail-under=80
- run: pytest tests/ -m security
- run: pytest tests/ -m contracts
- run: ruff check app/
- run: mypy app/
```

**Quebrou? → Não merga.**

---

## 📚 REFERÊNCIAS

- **Exemplo Real:** `backend/tests/test_analytics_routes.py` (53 testes, 100% passing)
- **Helpers:** `backend/tests/helpers/`
- **Middlewares:** `backend/app/middlewares/`
- **Definition of Done:** `docs/DEFINITION_OF_DONE.md`

---

## 💡 FILOSOFIA

> **"Se não está testado nos 4 pilares, não existe."**

Este blueprint não é burocracia.

É a forma de **escalar com qualidade**.

Novos devs → produtivos no dia 1.

Novos módulos → nível bancário desde o commit 1.

Sistema cresce → qualidade mantém.

**Sem esforço heroico. Só estrutura.**

---

🎯 **Última atualização:** 08/02/2026  
📦 **Versão:** 1.0  
✅ **Status:** Production-Ready
