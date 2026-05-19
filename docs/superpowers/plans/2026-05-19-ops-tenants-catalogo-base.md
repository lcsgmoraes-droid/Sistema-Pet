# Ops Tenants e Catalogo Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tenant management tab inside `/ops` with safe base catalog import actions.

**Architecture:** Add a backend service for tenant summaries and catalog import orchestration, expose it through admin routes, then add a focused React page under the existing Ops layout. Reuse the existing base catalog import service and template install audit tables.

**Tech Stack:** FastAPI, SQLAlchemy raw SQL for dynamic aggregate counts, pytest with SQLite fixtures, React/Vite, existing `api` client and `react-icons`.

---

### Task 1: Backend Contract Tests

**Files:**
- Create: `backend/tests/multi_tenant/test_ops_tenants_service.py`
- Create: `backend/tests/unit/test_ops_tenants_routes_contract.py`

- [ ] **Step 1: Write service tests**

Create a SQLite fixture with `tenants`, `users`, `user_tenants`, `produtos`, `clientes`, `pets`, `vendas`, `tenant_template_installs`, and source user data. Assert that `list_ops_tenants` returns counts, principal user, plan/billing fields, and catalog import status.

- [ ] **Step 2: Write route contract test**

Assert that `backend/app/routes/ops_tenants_routes.py` contains the `/admin/tenants` prefix, `require_admin`, preview/apply endpoints, and `confirm`.

- [ ] **Step 3: Run red tests**

Run:

```powershell
cd backend
$env:DATABASE_URL='sqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/multi_tenant/test_ops_tenants_service.py tests/unit/test_ops_tenants_routes_contract.py -q
```

Expected: fail because service and route do not exist yet.

### Task 2: Backend Service and Routes

**Files:**
- Create: `backend/app/services/ops_tenants_service.py`
- Create: `backend/app/routes/ops_tenants_routes.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Implement tenant summaries**

Add `list_ops_tenants(db, search=None, status=None, limit=100)` returning summary totals and tenant items with counts for products, clients, pets, sales and users.

- [ ] **Step 2: Implement import preview/apply helpers**

Add `preview_base_catalog_import(db, tenant_id)` and `apply_base_catalog_import(db, tenant_id, confirm, actor_user_id)` that resolve source tenant `admin@mlprohub.com.br`, choose the target principal user, and call `import_base_catalog`.

- [ ] **Step 3: Implement admin routes**

Expose `GET /admin/tenants`, `POST /admin/tenants/{tenant_id}/catalog-import/preview`, and `POST /admin/tenants/{tenant_id}/catalog-import/apply` with `require_admin`.

- [ ] **Step 4: Register router**

Import and include the router in `backend/app/main.py`.

- [ ] **Step 5: Run backend tests**

Run the same pytest command from Task 1. Expected: pass.

### Task 3: Ops Frontend

**Files:**
- Create: `frontend/src/pages/OpsTenants.jsx`
- Modify: `frontend/src/components/OpsLayout.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add route and nav item**

Lazy-load `OpsTenants`, add `/ops/tenants`, and add "Tenants" to the Ops side nav.

- [ ] **Step 2: Build OpsTenants page**

Fetch `/admin/tenants`, render compact metrics, filters, tenant table/cards and action buttons. Store the last preview by tenant ID and enable apply only after successful preview.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: build succeeds.

### Task 4: Final Verification

**Files:**
- All files above.

- [ ] **Step 1: Run focused backend tests**

```powershell
cd backend
$env:DATABASE_URL='sqlite:///:memory:'
.\.venv\Scripts\python.exe -m pytest tests/multi_tenant/test_ops_tenants_service.py tests/unit/test_ops_tenants_routes_contract.py tests/multi_tenant/test_base_catalog_import_service.py tests/multi_tenant/test_base_catalog_import_script.py -q
```

- [ ] **Step 2: Run frontend build**

```powershell
cd frontend
npm run build
```

- [ ] **Step 3: Finish branch**

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: adicionar gestao de tenants no ops" -Push
```
