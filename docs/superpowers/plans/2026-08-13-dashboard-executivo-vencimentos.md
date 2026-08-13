# Dashboard Executivo e Vencimentos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar uma abertura compacta do dashboard com faturamento, pedidos/unidades e lucro real das vendas, separando corretamente contas vencidas das que vencem hoje.

**Architecture:** O endpoint leve de resumo continuará consolidando os números essenciais sem chamar o relatório completo. Funções puras no frontend normalizam o contrato e alimentam cards pequenos, enquanto o componente da página fica responsável apenas por carregamento, composição e navegação.

**Tech Stack:** FastAPI, SQLAlchemy, Pytest, React 18, React Router, Tailwind CSS, Node test runner, Vite.

---

### Task 1: Contrato financeiro e regra de vencimento

**Files:**
- Modify: `backend/tests/unit/test_dashboard_resumo_numeric_types.py`
- Modify: `backend/tests/unit/test_dashboard_periodo_bounds_contract.py`
- Modify: `backend/app/dashboard_routes.py`

- [ ] **Step 1: Write the failing tests**

Estender o teste do resumo para exigir `vence_hoje` em contas a receber/pagar, `unidades` e `lucro` em vendas. Adicionar um teste de contrato exigindo que `obter_resumo_dashboard` use `now_brasilia().date()` e comparações `< hoje` e `== hoje`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH="$PWD\backend"
& 'C:\Users\lcs_g\Sistema-Pet\backend\.venv\Scripts\python.exe' -m pytest backend/tests/unit/test_dashboard_periodo_bounds_contract.py backend/tests/unit/test_dashboard_resumo_numeric_types.py -q
```

Expected: FAIL por ausência de `vence_hoje`, `unidades` e `lucro` e pelo uso atual de `now_brasilia()` sem `.date()`.

- [ ] **Step 3: Implement the minimal backend contract**

Em `obter_resumo_dashboard`:

```python
hoje = now_brasilia().date()
agora = now_brasilia()
inicio_periodo, fim_periodo = _intervalo_dias_calendario(periodo_dias, agora)
```

Somar separadamente saldos com `data_vencimento < hoje` e `data_vencimento == hoje`, carregar `Venda.itens`, somar as quantidades e ler `lucro` de `rentabilidade_snapshot` com `_snapshot_dict`.

- [ ] **Step 4: Run tests to verify they pass**

Executar o mesmo comando do passo 2 e esperar todos os testes verdes.

### Task 2: Indicadores executivos no frontend

**Files:**
- Modify: `frontend/scripts/test-dashboard-overview.mjs`
- Modify: `frontend/src/pages/dashboard/dashboardOverview.js`

- [ ] **Step 1: Write the failing frontend test**

Exigir que o resumo vazio contenha `vence_hoje`, `unidades` e `lucro`, e que `calculateDashboardIndicators` retorne `salesProfit`, `unitsSold`, `dueTodayReceivable` e `dueTodayPayable` sem misturá-los com `cashResult`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node frontend/scripts/test-dashboard-overview.mjs
```

Expected: FAIL porque os novos indicadores ainda não existem.

- [ ] **Step 3: Implement the minimal derived values**

Adicionar os campos ao resumo vazio e retornar os valores normalizados em `calculateDashboardIndicators`.

- [ ] **Step 4: Run test to verify it passes**

Executar o mesmo comando do passo 2 e esperar todos os testes verdes.

### Task 3: Composição compacta do dashboard

**Files:**
- Create: `frontend/scripts/test-dashboard-executive-layout.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/src/pages/dashboard/DashboardCards.jsx`
- Modify: `frontend/src/pages/DashboardFinanceiro.jsx`

- [ ] **Step 1: Write the failing layout contract**

O teste estrutural deve exigir três rótulos principais (`Faturamento`, `Pedidos / unidades`, `Lucro das vendas`), navegação do lucro para `/financeiro/dre`, um card `Vence hoje` e ausência do título alto `Visão geral do negócio`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
node frontend/scripts/test-dashboard-executive-layout.mjs
```

Expected: FAIL porque a composição antiga ainda possui quatro cards e o cabeçalho alto.

- [ ] **Step 3: Implement the compact cards and toolbar**

Criar `CompactMetricCard` em `DashboardCards.jsx`. Em `DashboardFinanceiro.jsx`, substituir o card de abertura por toolbar compacta, montar a grade principal de três cards e a grade secundária com saldo bancário, resultado de caixa, ticket médio, a receber e a pagar. Incluir `Pagamentos que vencem hoje` na área de atenção.

- [ ] **Step 4: Run frontend contracts**

Run:

```powershell
node frontend/scripts/test-dashboard-overview.mjs
node frontend/scripts/test-dashboard-executive-layout.mjs
```

Expected: todos os testes verdes.

### Task 4: Qualidade e entrega da branch

**Files:**
- Verify: `backend/app/dashboard_routes.py`
- Verify: `frontend/src/pages/DashboardFinanceiro.jsx`
- Verify: `frontend/src/pages/dashboard/DashboardCards.jsx`

- [ ] **Step 1: Run focused backend tests**

```powershell
$env:PYTHONPATH="$PWD\backend"
& 'C:\Users\lcs_g\Sistema-Pet\backend\.venv\Scripts\python.exe' -m pytest backend/tests/unit/test_dashboard_periodo_bounds_contract.py backend/tests/unit/test_dashboard_resumo_numeric_types.py -q
```

- [ ] **Step 2: Run frontend lint and build**

```powershell
npm --prefix frontend run lint:core
npm --prefix frontend run build
```

- [ ] **Step 3: Inspect the final diff and protected files**

```powershell
git status --short
git diff --check
git diff --stat
```

Confirmar que não há `frontend/dist`, segredos, dumps ou arquivos protegidos alterados.

- [ ] **Step 4: Commit and push through the repository flow**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: reorganiza dashboard executivo e vencimentos" -Push
```

- [ ] **Step 5: Open the pull request**

Abrir PR da branch `feat/20260813-dashboard-executivo-vencimentos` para `main`, informar testes executados e não iniciar deploy remoto sem autorização explícita do Lucas.
