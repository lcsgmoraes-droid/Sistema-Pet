# Reprocessar Custos de Vendas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual sale profitability reprocessing that updates sale stock movement costs from current product cost and refreshes the sales report.

**Architecture:** Put the financial mutation in a focused backend service, expose it through the sales report router, and keep the React list responsible only for selection, confirmation, and refresh. The horizontal scroll fix stays in the shared `DataTable` wrapper so this list benefits without a large table rewrite.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, React, Vite, Tailwind, lucide-react, react-hot-toast.

---

### Task 1: Backend Service

**Files:**
- Create: `backend/app/services/venda_rentabilidade_reprocessamento_service.py`
- Test: `backend/tests/unit/test_venda_rentabilidade_reprocessamento_service.py`

- [ ] Write a failing pytest that creates a fake finalized sale, a product with current `preco_custo`, an old stock movement cost, and verifies reprocessing updates `custo_unitario`, `valor_total`, `rentabilidade_snapshot["custo_produtos"]`, and `rentabilidade_snapshot["lucro"]`.
- [ ] Run `python -m pytest backend/tests/unit/test_venda_rentabilidade_reprocessamento_service.py -v` and confirm the missing service failure.
- [ ] Implement `reprocessar_rentabilidade_vendas(db, tenant_id, venda_ids=None, data_inicio=None, data_fim=None, canal_venda=None)` and helper functions to load tenant-safe sales, update movement costs, build the stock-cost map, and call `get_or_build_venda_rentabilidade_snapshot(..., force_refresh=True, persist_if_missing=True, estoque_custos_por_produto=mapa_corrigido)`.
- [ ] Run the unit test again and confirm it passes.

### Task 2: Backend Endpoint

**Files:**
- Modify: `backend/app/relatorio_vendas_routes.py`
- Test: `backend/tests/unit/test_relatorio_vendas_reprocessamento_contract.py`

- [ ] Write a contract test that imports the router and confirms `POST /vendas/reprocessar-rentabilidade` exists under the `/relatorios` prefix.
- [ ] Add Pydantic request/response models and the endpoint `@router.post("/vendas/reprocessar-rentabilidade")`.
- [ ] Validate that either `venda_ids` or `data_inicio`/`data_fim` is present; return HTTP 400 otherwise.
- [ ] Call the service, commit the transaction, and return the service summary.
- [ ] Run `python -m pytest backend/tests/unit/test_relatorio_vendas_reprocessamento_contract.py backend/tests/unit/test_venda_rentabilidade_reprocessamento_service.py -v`.

### Task 3: Frontend Controls

**Files:**
- Modify: `frontend/src/components/VendasFinanceiro.jsx`
- Modify: `frontend/src/components/financeiro/VendasListaPanel.jsx`
- Modify: `frontend/src/components/financeiro/VendasFinanceiroListaTable.jsx`

- [ ] Add selection state in `VendasFinanceiro.jsx` and a `reprocessarRentabilidadeVendas` handler that posts to `/relatorios/vendas/reprocessar-rentabilidade`, asks for confirmation with the number of vendas, shows toast loading/success/error, and calls `carregarDados()`.
- [ ] Pass selection props and reprocess handlers into `VendasListaPanel` and `VendasFinanceiroListaTable`.
- [ ] Add a compact actions menu in `VendasListaPanel` with options for selected sales and current period.
- [ ] Add checkbox column and one compact row action in `VendasFinanceiroListaTable`, using `event.stopPropagation()` for checkbox and action clicks.

### Task 4: Horizontal Scroll

**Files:**
- Modify: `frontend/src/components/ui/DataTable.jsx`

- [ ] Wrap the table in a scroll container with `overflow-x-auto` plus a top horizontal scrollbar synchronized with the main table scroll.
- [ ] Keep the table width stable so row hover and expanded rows do not shift.
- [ ] Run `npm run build` from `frontend`.

### Task 5: Finish

**Files:**
- All changed files from Tasks 1-4

- [ ] Run backend targeted tests.
- [ ] Run frontend build.
- [ ] Run `git status --short --branch`.
- [ ] Finish with `powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: reprocessar custos de vendas" -Push`.
