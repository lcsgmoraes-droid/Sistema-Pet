# RH e Multiacesso App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** corrigir ativacao/inativacao de funcionarios, fazer funcionario ativo vencer a fusao automatica de pessoas, e liberar multiplos perfis de app por pessoa.

**Status em 2026-06-13:** implementado e validado com testes focados, typecheck do app mobile, build do ERP e Alembic head `sv20260613a1`.

**Architecture:** manter compatibilidade com `clientes.tipo_cadastro`, `clientes.is_entregador` e os flags atuais do app, mas adicionar uma camada explicita de perfis liberados no app. O backend passa a retornar `available_profiles` e `perfil_operacional` selecionado; o ERP gerencia esses acessos em funcionario/pessoa; o app permite escolher no login e trocar depois.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React/Vite, React Native/Expo, pytest, testes unitarios de contrato JS.

---

### Task 1: RH ativar/inativar com protecao de regressao

**Files:**
- Modify: `backend/app/funcionarios_routes.py`
- Modify: `frontend/src/pages/RH/Funcionarios.jsx`
- Test: `backend/tests/unit/test_funcionarios_rh_status_contract.py`

- [x] **Step 1: Write the failing test**

Create a source-contract test asserting:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read_repo(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_funcionarios_backend_exposes_explicit_activate_endpoint():
    source = read_repo("app/funcionarios_routes.py")
    assert '@router.post("/{funcionario_id}/ativar"' in source
    assert "funcionario.ativo = True" in source

def test_funcionarios_page_shows_activate_button_for_inactive_rows():
    source = read_repo("../frontend/src/pages/RH/Funcionarios.jsx")
    assert "const ativar = async" in source
    assert "Ativar" in source
    assert "!f.ativo" in source
    assert "/ativar" in source
```

- [x] **Step 2: Run RED**

Run: `cd backend; pytest tests/unit/test_funcionarios_rh_status_contract.py -q`

Expected: fails because no `/ativar` endpoint and no `Ativar` button exist.

- [x] **Step 3: Implement minimal backend and frontend**

Add `POST /funcionarios/{funcionario_id}/ativar` setting `ativo=True`, returning the same response shape. In React, add `ativar(id)` and render green `Ativar` when `!f.ativo`.

- [x] **Step 4: Run GREEN**

Run: `cd backend; pytest tests/unit/test_funcionarios_rh_status_contract.py -q`

Expected: pass.

### Task 2: fazer funcionario ativo vencer fusao automatica

**Files:**
- Modify: `backend/app/services/pessoa_duplicate_service.py`
- Test: `backend/tests/unit/test_pessoa_duplicate_service.py`

- [x] **Step 1: Write the failing test**

Add tests showing automatic merge is still allowed, but an active employee is chosen as the principal:

```python
def test_escolher_pessoa_principal_prefere_funcionario_ativo_ao_cliente_ativo():
    cliente = _pessoa(id=10, nome="William", tipo_cadastro="cliente", email="william@example.com")
    funcionario = _pessoa(id=11, nome="William", tipo_cadastro="funcionario", ativo=True)

    principal = escolher_pessoa_principal(
        [cliente, funcionario],
        referencias_por_id={10: 20, 11: 0},
    )

    assert principal is funcionario

def test_avaliar_par_permite_fusao_automatica_entre_cliente_e_funcionario_sem_conflitos():
    cliente = _pessoa(id=10, nome="William", tipo_cadastro="cliente")
    funcionario = _pessoa(id=11, nome="william", tipo_cadastro="funcionario")

    decisao = avaliar_par_duplicidade_pessoas(cliente, funcionario)

    assert decisao.pode_fundir_automaticamente is True

def test_avaliar_par_permite_fusao_automatica_entre_clientes_com_nome_igual():
    cliente_a = _pessoa(id=10, nome="Maria Carolina", tipo_cadastro="cliente")
    cliente_b = _pessoa(id=11, nome="maria carolina", tipo_cadastro="cliente")

    decisao = avaliar_par_duplicidade_pessoas(cliente_a, cliente_b)

    assert decisao.pode_fundir_automaticamente is True
```

- [x] **Step 2: Run RED**

Run: `cd backend; pytest tests/unit/test_pessoa_duplicate_service.py -q`

Expected: fails because active employee does not outrank a customer with more references/completeness.

- [x] **Step 3: Implement principal ranking**

Add `_prioridade_perfil_pessoa()` so active `tipo_cadastro == "funcionario"` wins over common customer records before reference/completeness scoring. Keep automatic merge eligibility based on name and strong-field conflicts.

- [x] **Step 4: Run GREEN**

Run: `cd backend; pytest tests/unit/test_pessoa_duplicate_service.py -q`

Expected: pass.

### Task 3: backend de perfis do app

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/alembic/versions/sv20260613a1_app_access_profiles.py`
- Create: `backend/app/services/app_access_profile_service.py`
- Modify: `backend/app/routes/ecommerce_auth.py`
- Modify: `backend/app/routes/app_mobile_routes.py`
- Test: `backend/tests/unit/test_app_access_profiles.py`
- Test: `backend/tests/unit/test_ecommerce_mobile_tenant_context.py`

- [x] **Step 1: Write failing service tests**

Test that a linked employee with `tipo_cadastro="funcionario"` and `is_entregador=True` yields profiles `cliente`, `funcionario`, `entregador`, and selected profile changes the boolean flags consistently.

- [x] **Step 2: Run RED**

Run: `cd backend; pytest tests/unit/test_app_access_profiles.py -q`

Expected: fails because the service does not exist.

- [x] **Step 3: Implement model, migration and service**

Create table `app_access_profiles` with `tenant_id`, `user_id`, `cliente_id`, `profile_type`, `is_active`, timestamps, unique `(tenant_id, user_id, profile_type, cliente_id)`. Service returns derived profiles from current `clientes` plus explicit grants.

- [x] **Step 4: Wire auth serialization**

Add `available_profiles` and `selected_profile` to `/ecommerce/auth/login` and `/ecommerce/auth/perfil`. Add `/ecommerce/auth/select-profile` to validate requested profile and return updated user payload.

- [x] **Step 5: Run GREEN**

Run: `cd backend; pytest tests/unit/test_app_access_profiles.py tests/unit/test_ecommerce_mobile_tenant_context.py -q`

Expected: pass.

### Task 4: ERP controls for app access

**Files:**
- Modify: `backend/app/funcionarios_routes.py`
- Modify: `frontend/src/pages/RH/Funcionarios.jsx`
- Test: `backend/tests/unit/test_funcionarios_rh_status_contract.py`

- [x] **Step 1: Write failing test**

Extend the contract test to assert `app_access_profiles` appears in the route schema/response and the page renders the "Acessos do app" controls with Cliente, Funcionario, Entregador, Veterinario.

- [x] **Step 2: Run RED**

Run: `cd backend; pytest tests/unit/test_funcionarios_rh_status_contract.py -q`

Expected: fails.

- [x] **Step 3: Implement minimal controls**

Expose app access fields on `FuncionarioResponse` and save endpoint. In the React form, add checkboxes under "Acessos do app" and send them in the payload.

- [x] **Step 4: Run GREEN**

Run: `cd backend; pytest tests/unit/test_funcionarios_rh_status_contract.py -q`

Expected: pass.

### Task 5: app login picker and in-app switcher

**Files:**
- Modify: `app-mobile/src/types/index.ts`
- Modify: `app-mobile/src/services/auth.service.ts`
- Modify: `app-mobile/src/store/auth.store.ts`
- Modify: `app-mobile/src/screens/auth/LoginScreen.tsx`
- Modify: `app-mobile/src/screens/profile/ProfileScreen.tsx`
- Test: `backend/tests/unit/test_app_mobile_multi_profile_contract.py`

- [x] **Step 1: Write failing source-contract test**

Assert the app types include `available_profiles`, auth service includes `selectProfile`, store includes `selectProfile`, Login renders profile choices, and Profile renders a switch action.

- [x] **Step 2: Run RED**

Run: `cd backend; pytest tests/unit/test_app_mobile_multi_profile_contract.py -q`

Expected: fails.

- [x] **Step 3: Implement minimal app behavior**

After login, if more than one profile is available, keep user authenticated but show profile choices on the login screen until selection. `selectProfile` updates the token/user if backend returns a token, or updates the user payload if token stays the same. Profile screen shows "Trocar perfil" when multiple profiles exist.

- [x] **Step 4: Run GREEN**

Run: `cd backend; pytest tests/unit/test_app_mobile_multi_profile_contract.py -q`

Expected: pass.

### Task 6: validation and production data repair plan

**Files:**
- Modify: docs if needed

- [x] **Step 1: Run targeted tests**

Run:

```powershell
cd backend; pytest tests/unit/test_funcionarios_rh_status_contract.py tests/unit/test_pessoa_duplicate_service.py tests/unit/test_app_access_profiles.py tests/unit/test_app_mobile_multi_profile_contract.py -q
```

- [x] **Step 2: Build frontend if `frontend/src` changed**

Run: `cd frontend; npm run build`

- [x] **Step 3: Validate app TypeScript if available**

Run the existing mobile lint/typecheck command if present in `app-mobile/package.json`.

- [ ] **Step 4: Decide production data fix**

After deploy, reactivate `clientes.id IN (10466, 10467)` through the official API/UI or an audited SQL update only if Lucas explicitly confirms the data repair. The root cause must already be fixed in Git before any data change.
