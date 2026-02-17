# 🐾 Sistema Pet - Backend Multi-Tenant

Backend FastAPI para gestão completa de petshops e clínicas veterinárias com isolamento multi-tenant garantido.

## 🔒 REGRA ABSOLUTA — MULTI-TENANT

**É ESTRITAMENTE PROIBIDO:**

- ❌ Criar rotas sem `Depends(get_current_user_and_tenant)`
- ❌ Executar queries sem filtro por `tenant_id`
- ❌ Criar registros sem `tenant_id`
- ❌ Usar `Depends(get_current_user)` isolado em rotas de negócio
- ❌ Filtrar queries por `user_id` em vez de `tenant_id`

**Qualquer PR que viole essas regras DEVE ser recusado imediatamente.**

## ✅ Validação Automática

Antes de qualquer deploy ou merge, execute:

```bash
cd backend
python validate_multitenant_integrity.py
```

**Resultado esperado:**
```
✅ VALIDAÇÃO MULTI-TENANT: 100% OK
🔒 ISOLAMENTO POR TENANT: GARANTIDO
🎉 BACKEND FECHADO E PRONTO PARA PRODUÇÃO
```

Se aparecer **QUALQUER** erro crítico, corrija antes de prosseguir.

## 📋 Padrão Obrigatório

### Estrutura de Rota Correta

```python
from app.auth import get_current_user_and_tenant

@router.get("/endpoint")
def minha_rota(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    # ✅ OBRIGATÓRIO: Unpacking
    current_user, tenant_id = user_and_tenant
    
    # ✅ OBRIGATÓRIO: Filtro por tenant_id
    registros = db.query(Model).filter(
        Model.tenant_id == tenant_id
    ).all()
    
    # ✅ OBRIGATÓRIO: Criação com tenant_id
    novo = Model(
        tenant_id=tenant_id,
        campo="valor"
    )
    db.add(novo)
    db.commit()
    
    return registros
```

### ❌ Erros Comuns (NUNCA FAÇA ISSO)

```python
# ❌ ERRADO: get_current_user isolado
@router.get("/endpoint")
def rota_errada(
    current_user: User = Depends(get_current_user),  # ❌ PROIBIDO!
    db: Session = Depends(get_session)
):
    pass

# ❌ ERRADO: Query sem tenant_id
registros = db.query(Model).filter(
    Model.user_id == current_user.id  # ❌ NUNCA!
).all()

# ❌ ERRADO: Criação sem tenant_id
novo = Model(
    user_id=current_user.id,  # ❌ PROIBIDO!
    campo="valor"
)
```

## 📊 Status de Isolamento

| Módulo | Status | Rotas Corrigidas |
|--------|--------|------------------|
| **Compras** | ✅ 100% | Todas |
| **Caixa/Financeiro** | ✅ 100% | Todas |
| **Produtos/Estoque** | ✅ 100% | Todas |
| **Clientes** | ✅ 100% | 34 rotas |
| **PDV/Vendas** | ✅ 100% | 16 rotas |
| **Importação** | ✅ 100% | Pessoas + Produtos |
| **Lembretes** | ✅ 100% | 8 rotas |
| **Calculadora** | ✅ 100% | 2 rotas |
| **Cliente Info PDV** | ✅ 100% | 2 rotas |

**Total:** 100% do backend isolado por tenant

## 🚀 Instalação e Execução

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar .env
cp .env.example .env

# Executar migrações
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

## 🧪 Testes

```bash
# Validar multi-tenant
python validate_multitenant_integrity.py

# Executar testes unitários
pytest tests/

# Executar testes de integração
pytest tests/integration/
```

## 📚 Documentação

- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI:** http://localhost:8000/openapi.json

## 🛡️ Segurança

- ✅ Isolamento total por `tenant_id` em TODAS as operações
- ✅ Validação automática em CI/CD
- ✅ Zero vazamento de dados entre empresas
- ✅ Auditoria completa de acessos

## 📞 Suporte

Para dúvidas sobre multi-tenancy ou padrões do backend, consulte:
- `PDV_VENDAS_CORRECAO_COMPLETA_BACKEND_FECHADO.md`
- `CLIENTES_CORRECAO_MULTI_TENANT_COMPLETA.md`
- `validate_multitenant_integrity.py`

---

**⚠️ LEMBRE-SE: QUALQUER CÓDIGO QUE NÃO RESPEITE O ISOLAMENTO POR TENANT SERÁ REJEITADO.**
