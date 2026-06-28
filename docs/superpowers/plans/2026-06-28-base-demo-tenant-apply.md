# Base Demo Tenant Apply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o seed da base demo de marketing seja preparado para um tenant real por e-mail, mantendo dry-run como modo padrao e bloqueando uso indevido em producao.

**Architecture:** O script `scripts/aplicar_seed_base_demo_marketing.py` continua sendo a entrada operacional. A primeira fatia adiciona o contexto `tenant_email` no contrato, resolve tenant/usuario em helper testavel e prepara o CLI para dry-run identificado; aplicacao real via SQLAlchemy fica protegida por `--apply` e guardas explicitos.

**Tech Stack:** Python, SQLAlchemy do backend, scripts de teste Python existentes em `scripts/`.

---

### Task 1: Tenant Email Contract

**Files:**
- Modify: `scripts/test_marketing_demo_seed_apply.py`
- Modify: `scripts/aplicar_seed_base_demo_marketing.py`

- [ ] **Step 1: Write the failing test**

Add assertions that `apply_seed_plan(..., tenant_email="atacadaopetpp@gmail.com")` includes `tenant_email` in the result and that CLI dry-run accepts `--tenant-email atacadaopetpp@gmail.com`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/test_marketing_demo_seed_apply.py`
Expected: FAIL because `tenant_email` is not accepted yet.

- [ ] **Step 3: Write minimal implementation**

Add optional `tenant_email` parameter to `apply_seed_plan`, include it in the result, add `--tenant-email` to CLI, and pass it through in dry-run.

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/test_marketing_demo_seed_apply.py`
Expected: PASS with `Marketing demo seed apply contract OK`.

### Task 2: Tenant Resolver

**Files:**
- Modify: `scripts/test_marketing_demo_seed_apply.py`
- Modify: `scripts/aplicar_seed_base_demo_marketing.py`

- [ ] **Step 1: Write the failing test**

Add a fake session/query test for `resolve_tenant_context_by_email(fake_db, "atacadaopetpp@gmail.com")`, expecting tenant id, user id, and normalized email.

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/test_marketing_demo_seed_apply.py`
Expected: FAIL because the resolver does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement a small resolver that normalizes e-mail, queries `User.email`, requires `tenant_id`, and raises clear `ValueError` for missing user or missing tenant.

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/test_marketing_demo_seed_apply.py`
Expected: PASS.

### Task 3: Safe Apply Entry

**Files:**
- Modify: `scripts/test_marketing_demo_seed_apply.py`
- Modify: `scripts/aplicar_seed_base_demo_marketing.py`
- Modify: `docs/marketing/base-demo/README.md` or the closest existing package doc

- [ ] **Step 1: Write the failing test**

Add CLI assertions that non-dry-run without `--apply` still fails, `--apply` without `--tenant-email` fails, and production remains blocked.

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/test_marketing_demo_seed_apply.py`
Expected: FAIL for missing flags/guards.

- [ ] **Step 3: Write minimal implementation**

Add `--apply` as the only way to leave dry-run mode, require `--tenant-email`, and keep production blocked unless the existing guard explicitly allows it in code tests only.

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/test_marketing_demo_seed_apply.py`
Expected: PASS.

### Task 4: Documentation and Verification

**Files:**
- Modify: `docs/marketing/BASE_DEMO_GRAVACAO.md`
- Modify: `docs/INDICE_OPERACIONAL.md`

- [ ] **Step 1: Update docs**

Document the dry-run command with `--tenant-email atacadaopetpp@gmail.com`, explain that real apply is only for DEV/demo and not a production deploy.

- [ ] **Step 2: Run focused checks**

Run:
`python scripts/test_marketing_demo_seed_apply.py`
`python scripts/test_marketing_demo_seed_plan.py`
`python scripts/test_marketing_demo_package.py`
Expected: all pass.

- [ ] **Step 3: Finish branch**

Run `git status --short`, then `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: prepara seed demo por tenant email" -Push`.
