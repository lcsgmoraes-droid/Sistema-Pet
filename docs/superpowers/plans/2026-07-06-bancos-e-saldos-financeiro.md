# Bancos e Saldos Financeiro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar a tela de ajuste pontual em uma tela Financeiro > Bancos, com saldos, extrato por conta e ajuste via modal auditavel.

**Architecture:** Reaproveitar o endpoint de contas bancarias e o endpoint de movimentacoes por conta ja existentes. A tela frontend fica em uma pagina focada, com a lista de bancos, extrato da conta selecionada e modal para confirmar ajuste de saldo.

**Tech Stack:** React/Vite, `api` axios local, componentes UI existentes (`PageHeader`, `DataTable`, `MetricCard`, `CurrencyInput`), FastAPI ja existente para contas bancarias.

---

### Task 1: Contrato da tela Bancos

**Files:**
- Modify: `backend/tests/unit/test_ajuste_saldo_bancario_financeiro_contract.py`

- [ ] **Step 1: Write the failing test**

```python
def test_bancos_fica_no_modulo_financeiro_com_extrato_e_modal():
    lazy_pages = _read(FRONTEND_ROOT / "app" / "lazyPages.jsx")
    finance_routes = _read(FRONTEND_ROOT / "app" / "routes" / "FinanceRoutes.jsx")
    menu_config = _read(FRONTEND_ROOT / "components" / "layout" / "menuConfig.js")
    bancos_page = _read(FRONTEND_ROOT / "pages" / "BancosFinanceiro.jsx")

    assert "BancosFinanceiro" in lazy_pages
    assert 'path="financeiro/bancos"' in finance_routes
    assert 'path: "/financeiro/bancos"' in menu_config
    assert 'label: "Bancos"' in menu_config
    assert "Extrato" in bancos_page
    assert "modalAjuste" in bancos_page
    assert "/movimentacoes" in bancos_page
    assert "/ajustar-saldo" in bancos_page
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/unit/test_ajuste_saldo_bancario_financeiro_contract.py -q`

Expected: FAIL porque `BancosFinanceiro.jsx` e a rota `/financeiro/bancos` ainda nao existem.

### Task 2: Implementar tela Financeiro > Bancos

**Files:**
- Create: `frontend/src/pages/BancosFinanceiro.jsx`
- Delete: `frontend/src/pages/AjusteSaldosBancarios.jsx`
- Modify: `frontend/src/app/lazyPages.jsx`
- Modify: `frontend/src/app/routes/FinanceRoutes.jsx`
- Modify: `frontend/src/components/layout/menuConfig.js`
- Modify: `frontend/src/components/FluxoCaixa.jsx`

- [ ] **Step 1: Build the page**

Criar `BancosFinanceiro.jsx` com:
- cards de saldo total, conta selecionada, entradas e saidas do extrato carregado;
- lista lateral de contas ativas;
- extrato da conta selecionada carregado por `GET /contas-bancarias/{id}/movimentacoes`;
- botao `Ajustar saldo` que abre modal;
- modal com saldo real, motivo, diferenca calculada e confirmacao por `POST /contas-bancarias/{id}/ajustar-saldo`.

- [ ] **Step 2: Wire route and menu**

Trocar o lazy export para `BancosFinanceiro`, rota para `financeiro/bancos`, menu para `Financeiro > Bancos` e atalho do Fluxo de Caixa para `/financeiro/bancos`.

- [ ] **Step 3: Run tests and build**

Run:
`python -m pytest backend/tests/unit/test_ajuste_saldo_bancario_financeiro_contract.py -q`
`npm run lint:core`
`npm run build`

Expected: todos com exit code 0.
