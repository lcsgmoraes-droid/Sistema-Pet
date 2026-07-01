# Menu Favoritos Por Usuario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build synced menu favorites per user so common routes such as PDV and Listar Produtos appear as quick shortcuts on every computer.

**Architecture:** Add a tenant-scoped backend model and authenticated routes under `/usuarios/me/menu-favoritos`. The frontend keeps the existing menu config as the source of available routes, filters favorites against the user's allowed menu, and saves the full ordered list to the backend.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React, Axios, react-icons, Node test scripts.

---

### Task 1: Backend Model, Migration, And Routes

**Files:**
- Create: `backend/app/usuario_menu_favoritos_models.py`
- Create: `backend/alembic/versions/uv20260630a1_create_usuario_menu_favoritos.py`
- Modify: `backend/app/usuarios_routes.py`
- Modify: `backend/app/main_routers.py`
- Test: `backend/tests/unit/test_usuario_menu_favoritos_contract.py`

- [ ] **Step 1: Write the failing backend contract test**

Create `backend/tests/unit/test_usuario_menu_favoritos_contract.py` checking that the model table name is `usuario_menu_favoritos`, that the migration creates indexes/unique constraint, and that `usuarios_routes.py` exposes `GET` and `PUT` at `/me/menu-favoritos`.

- [ ] **Step 2: Run the backend contract test and confirm failure**

Run: `python -m pytest backend/tests/unit/test_usuario_menu_favoritos_contract.py -q`

Expected: FAIL because the model and routes do not exist yet.

- [ ] **Step 3: Implement the model and migration**

Add a `UsuarioMenuFavorito` model with `user_id`, `path`, `label`, `icon_key`, and `position`. Add an Alembic migration creating the table with foreign key to `users.id`, tenant indexes, and unique constraint on `tenant_id`, `user_id`, `path`.

- [ ] **Step 4: Implement API schemas and routes**

In `usuarios_routes.py`, add `MenuFavoritoItem`, `MenuFavoritosPayload`, `listar_meus_menu_favoritos`, and `salvar_meus_menu_favoritos`. Validate max 8 items, trim labels/paths, replace the current list atomically, and return ordered items.

- [ ] **Step 5: Run backend contract test**

Run: `python -m pytest backend/tests/unit/test_usuario_menu_favoritos_contract.py -q`

Expected: PASS.

### Task 2: Frontend Favorite Utilities And API

**Files:**
- Create: `frontend/src/components/layout/menuFavorites.js`
- Create: `frontend/scripts/test-menu-favorites.mjs`
- Modify: `frontend/src/components/layout/menuConfig.js`
- Modify: `frontend/src/components/layout/menuConfig.test.mjs`

- [ ] **Step 1: Write utility tests**

Create `frontend/scripts/test-menu-favorites.mjs` covering flattening menu items, filtering saved favorites by allowed paths, toggling add/remove, and enforcing 8 favorites.

- [ ] **Step 2: Run utility tests and confirm failure**

Run: `node frontend/scripts/test-menu-favorites.mjs`

Expected: FAIL because `menuFavorites.js` does not exist.

- [ ] **Step 3: Implement utilities**

Implement `flattenMenuItemsForFavorites`, `normalizeMenuFavorites`, `buildVisibleMenuFavorites`, and `toggleMenuFavorite`. Export `MAX_MENU_FAVORITES = 8`.

- [ ] **Step 4: Add stable icon keys to menu config**

Add `iconKey` to menu and submenu items that need favorites. Use existing labels and paths; do not change route behavior.

- [ ] **Step 5: Run frontend utility tests**

Run: `node frontend/scripts/test-menu-favorites.mjs`

Expected: PASS.

### Task 3: Frontend UI Integration

**Files:**
- Modify: `frontend/src/components/Layout.jsx`
- Modify: `frontend/src/components/layout/SidebarMenu.jsx`

- [ ] **Step 1: Load and save favorites in Layout**

Use `api.get("/usuarios/me/menu-favoritos")` on authenticated layout load and `api.put("/usuarios/me/menu-favoritos", { items })` when toggling. Keep a local optimistic state and rollback on API failure.

- [ ] **Step 2: Render favorites bar**

Render a compact top bar above page content only when visible favorites exist. Each favorite is a `Link` with the existing icon and label.

- [ ] **Step 3: Render star buttons in sidebar**

Pass `favoritePaths` and `onToggleFavorite` to `SidebarMenu`. Show `FiStar` as a small icon button for top-level items and subitems. Stop event propagation so starring does not navigate or open submenus.

- [ ] **Step 4: Verify frontend tests and build**

Run: `node frontend/scripts/test-menu-favorites.mjs`

Expected: PASS.

Run: `npm run build` from `frontend`

Expected: production build succeeds.

### Task 4: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run backend focused test**

Run: `python -m pytest backend/tests/unit/test_usuario_menu_favoritos_contract.py -q`

Expected: PASS.

- [ ] **Step 2: Run frontend focused test**

Run: `node frontend/scripts/test-menu-favorites.mjs`

Expected: PASS.

- [ ] **Step 3: Check git status**

Run: `git status --short`

Expected: only files from this feature appear.
