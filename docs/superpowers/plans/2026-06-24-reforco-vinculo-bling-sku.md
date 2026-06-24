# Reforco Vinculo Bling SKU Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Bling product linkage reliable, strict by equal SKU for automation, and easier to operate from the sync screen without unnecessary Bling requests.

**Architecture:** Centralize safe linkage validation in the backend, reuse catalog snapshots for suggestions, and keep automatic actions limited to exact SKU matches. The frontend becomes a cache-first operational screen with clear sections for Bling items missing in CorePet, exact SKU link suggestions, linked/sync problems, and local products that may optionally be created in Bling later.

**Tech Stack:** FastAPI/SQLAlchemy backend, pytest unit tests, React/Vite frontend, existing `api` client and `EstoqueBling` component.

---

### Task 1: Backend Safe Link Contract

**Files:**
- Modify: `backend/app/bling_sync/product_matching.py`
- Modify: `backend/app/bling_sync_routes.py`
- Modify: `backend/app/services/bling_sync_service.py`
- Test: `backend/tests/unit/test_bling_product_matching.py`
- Test: `backend/tests/unit/test_bling_sync_routes_safe_link.py`
- Test: `backend/tests/unit/test_bling_sync_service_auto_link.py`

- [ ] **Step 1: Write failing tests for strict SKU normalization**

Create tests proving automatic SKU match treats trim/case as equal but does not collapse punctuation.

- [ ] **Step 2: Write failing tests for duplicate Bling ID guard**

Create tests proving `_upsert_sync_vinculo` refuses to link the same `bling_produto_id` to a different product in the same tenant.

- [ ] **Step 3: Write failing tests for service auto-link**

Create tests proving the nightly auto-link only links exact SKU/codigo matches and does not link by name or first search result.

- [ ] **Step 4: Implement minimal backend helpers**

Add conservative SKU match helpers, conflict guard, and route/service usage.

- [ ] **Step 5: Run backend targeted tests**

Run: `python -m pytest backend/tests/unit/test_bling_product_matching.py backend/tests/unit/test_bling_sync_routes_safe_link.py backend/tests/unit/test_bling_sync_service_auto_link.py backend/tests/unit/test_bling_sync_service_tenant_context.py backend/tests/unit/test_bling_sync_produtos_routes_contract.py -q`

Expected: all selected tests pass.

### Task 2: Cache-First Sync Screen

**Files:**
- Modify: `frontend/src/components/EstoqueBling.jsx`
- Modify: `frontend/src/components/estoqueBlingUtils.js` if needed

- [ ] **Step 1: Review current UI structure**

Identify existing state, data loading, tabs/sections, and actions in `EstoqueBling.jsx`.

- [ ] **Step 2: Simplify operational sections**

Reshape screen copy and sections around: Bling sem cadastro local, Sugestoes por SKU igual, Problemas de sync, Produto local sem Bling.

- [ ] **Step 3: Preserve cache-first behavior**

Ensure the screen opens with cached dashboard and only calls force refresh when the user clicks refresh.

- [ ] **Step 4: Make safe actions obvious**

Use individual and batch actions only for exact SKU matches; keep non-exact/name matches out of automatic flow.

- [ ] **Step 5: Run frontend build**

Run: `npm --prefix frontend run build`

Expected: build exits 0.

### Task 3: Verification And Review

**Files:**
- Review all modified files with `git diff`

- [ ] **Step 1: Run backend targeted tests again**

Run the backend command from Task 1 Step 5.

- [ ] **Step 2: Run frontend build again**

Run: `npm --prefix frontend run build`

- [ ] **Step 3: Inspect git diff**

Run: `git diff --stat` and `git diff --check`.

- [ ] **Step 4: Prepare final summary**

Report changed files, test commands, and whether deployment was intentionally not performed without explicit production authorization.
