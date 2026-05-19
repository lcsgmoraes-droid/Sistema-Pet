# Orcamento Veterinario MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable veterinary budget flow with estimated cost, sale price, margin, and no stock movement until real usage.

**Architecture:** Add a small backend slice under `/vet/orcamentos` with persisted budget headers/items and deterministic financial calculations. Reuse the existing veterinary catalog/product data for costs and prices, then expose a compact frontend panel in consultation and hospitalization flows.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, React/Vite, node:test.

---

### Task 1: Backend Models, Migration, And Calculation Contract

**Files:**
- Modify: `backend/app/veterinario_models.py`
- Modify: `backend/app/veterinario_schemas.py`
- Create: `backend/app/veterinario_orcamentos.py`
- Create: `backend/alembic/versions/ow20260518a1_create_vet_orcamentos.py`
- Test: `backend/tests/unit/test_vet_orcamentos_mvp.py`

- [ ] Write a failing pytest that calls `montar_item_orcamento_catalogo` with a catalog procedure and product-backed insumos, expecting cost, sale, and margin totals.
- [ ] Write a failing pytest that calls `montar_item_orcamento_produto` and expects `preco_custo` and `preco_venda` to become suggested cost/sale values.
- [ ] Add `OrcamentoVet` and `OrcamentoVetItem` SQLAlchemy models with tenant fields inherited from `BaseTenantModel`.
- [ ] Add Pydantic schemas for budget create/update/response.
- [ ] Implement pure calculation helpers in `veterinario_orcamentos.py`.
- [ ] Add Alembic migration with idempotent table/index creation.
- [ ] Run `pytest backend/tests/unit/test_vet_orcamentos_mvp.py -q` and confirm the tests pass.

### Task 2: Backend Routes

**Files:**
- Create: `backend/app/veterinario_orcamentos_routes.py`
- Modify: `backend/app/veterinario_routes.py`
- Test: `backend/tests/unit/test_vet_orcamentos_mvp.py`

- [ ] Write a failing route-contract test asserting `veterinario_routes.router` exposes `GET /vet/orcamentos`, `POST /vet/orcamentos`, `GET /vet/orcamentos/{orcamento_id}`, and `PATCH /vet/orcamentos/{orcamento_id}`.
- [ ] Implement create/list/get/update routes with tenant validation for consultation, hospitalization, pet, and client links.
- [ ] Recalculate header totals from items before commit.
- [ ] Ensure create/update never call the stock movement helpers.
- [ ] Run the focused pytest command and confirm it passes.

### Task 3: Frontend Budget Utilities And API

**Files:**
- Modify: `frontend/src/pages/veterinario/vetApi.js`
- Create: `frontend/src/pages/veterinario/orcamentos/orcamentoUtils.js`
- Create: `frontend/src/pages/veterinario/orcamentos/orcamentoUtils.test.mjs`

- [ ] Write failing node tests for item normalization, total calculation, and hospitalization daily estimate.
- [ ] Implement frontend utility functions for budget rows and totals.
- [ ] Add vetApi methods for create/list/get/update budgets.
- [ ] Run `node --test frontend/src/pages/veterinario/orcamentos/orcamentoUtils.test.mjs`.

### Task 4: Consultation And Hospitalization MVP UI

**Files:**
- Create: `frontend/src/pages/veterinario/orcamentos/OrcamentoMvpPanel.jsx`
- Modify: `frontend/src/pages/veterinario/VetConsultaForm.jsx`
- Modify: `frontend/src/pages/veterinario/internacoes/InternacaoDetalhe.jsx`

- [ ] Add a compact panel that accepts budget context, catalog procedures, and stock products.
- [ ] Show estimated cost, suggested sale, charged sale, and margin.
- [ ] In consultation, render the panel near performed procedures when a consultation id exists.
- [ ] In hospitalization detail, render the panel with predicted days and existing hospitalization id.
- [ ] Keep all budget actions separate from real procedure/insumo launch actions.

### Task 5: Validation

**Files:**
- No code files expected.

- [ ] Run backend focused tests for veterinary budget and stock helpers.
- [ ] Run frontend budget utility tests.
- [ ] Run `npm run typecheck` or the nearest available frontend check if configured.
- [ ] Run `git status --short --branch` and commit focused changes.
