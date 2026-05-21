# Composicao Remuneracao Funcionarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que cargo e funcionario calculem folha oficial, descontos, encargos, provisoes e complemento interno pago.

**Architecture:** O cargo guarda regras padrao de folha. O funcionario herda o cargo, mas pode informar acordo liquido/complemento e sobrescrever o salario base para manter historico gerencial. O calculo fica em um service puro de RH e as rotas apenas persistem/retornam o resumo.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React/Vite, pytest.

---

### Task 1: Modelo E Calculo RH

**Files:**
- Modify: `backend/app/cargo_models.py`
- Modify: `backend/app/models.py`
- Create: `backend/app/services/remuneracao_service.py`
- Create: `backend/alembic/versions/oy20260521a2_add_remuneracao_funcionarios.py`
- Test: `backend/tests/unit/test_remuneracao_funcionarios_contract.py`

- [x] **Step 1: Write failing tests**

Create contract tests covering the Jefferson example: salario base 2098, INSS funcionario 164.50, FGTS 167.84, liquido combinado 2800, complemento calculado 866.50.

- [x] **Step 2: Run tests and verify failure**

Run: `python -m pytest backend/tests/unit/test_remuneracao_funcionarios_contract.py -q`
Expected: FAIL because the service and fields do not exist.

- [x] **Step 3: Implement service and schema fields**

Add cargo payroll defaults, funcionario agreement fields, and a pure calculation function returning base folha, descontos, liquido holerite, complemento, encargos, provisoes and custo total.

- [x] **Step 4: Run tests and verify pass**

Run: `python -m pytest backend/tests/unit/test_remuneracao_funcionarios_contract.py -q`
Expected: PASS.

### Task 2: Rotas De Cargo E Funcionario

**Files:**
- Modify: `backend/app/cargos_routes.py`
- Modify: `backend/app/funcionarios_routes.py`
- Test: `backend/tests/unit/test_remuneracao_funcionarios_contract.py`

- [x] **Step 1: Extend request/response contracts**

Expose regime, descontos, provisoes, acordo liquido and resumo remuneracao on existing endpoints.

- [x] **Step 2: Add read endpoint**

Add `GET /funcionarios/{id}/remuneracao` for the monthly composition preview.

- [x] **Step 3: Run tests**

Run the contract test and import checks for routes.

### Task 3: Interface RH

**Files:**
- Modify: `frontend/src/pages/Cadastros/Cargos.jsx`
- Modify: `frontend/src/pages/RH/Funcionarios.jsx`
- Test: `backend/tests/unit/test_remuneracao_funcionarios_contract.py`

- [x] **Step 1: Extend cargo form**

Add regime, INSS funcionario, desconto transporte/outros, provisao flags and simple/no-encargo mode.

- [x] **Step 2: Extend funcionario form**

Add salario override, liquido combinado, complemento manual/automatico and composition panel.

- [x] **Step 3: Build and verify**

Run: `npm run build` in `frontend`.
