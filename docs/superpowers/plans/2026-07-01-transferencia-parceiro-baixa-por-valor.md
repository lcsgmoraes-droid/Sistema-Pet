# Transferencia Parceiro Baixa Por Valor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar baixa por valor para transferencias de parceiro, com revisao por checkbox, baixa financeira, acerto e produto devolvido.

**Architecture:** A regra de distribuicao e aplicacao fica em um service backend novo, chamado por um router pequeno incluido no router atual de transferencia parceiro. O frontend ganha um painel dedicado e helpers puros para manter os controllers e componentes existentes pequenos.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, React, Vite, node:test.

---

## File Structure

- Create: `backend/app/estoque/transferencia_parceiro_baixa_lote_schemas.py`
  - Schemas de preview, confirmacao e resposta da baixa por valor.
- Create: `backend/app/estoque/transferencia_parceiro_baixa_lote_service.py`
  - Busca transferencias abertas, calcula distribuicao e aplica baixa financeira/acerto/devolucao.
- Create: `backend/app/estoque/transferencia_parceiro_baixa_lote_routes.py`
  - Endpoints `preview-baixa-lote` e `baixa-lote`.
- Modify: `backend/app/estoque_transferencia_parceiro_routes.py`
  - Incluir o novo subrouter sem concentrar logica no arquivo principal.
- Modify: `backend/tests/unit/test_estoque_transferencia_parceiro_routes_contract.py`
  - Cobrir registro do novo router e manter limite de arquivos.
- Create: `backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py`
  - Testes unitarios puros da distribuicao e validacoes centrais.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.js`
  - Helpers puros para distribuicao local e montagem de payload.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs`
  - Testes dos helpers novos.
- Create: `frontend/src/pages/estoqueTransferenciaParceiro/BaixaLoteTransferenciaPanel.jsx`
  - Painel de baixa por valor com modo, forma de pagamento, resumo e lista.
- Create: `frontend/src/pages/estoqueTransferenciaParceiro/BaixaLoteTransferenciaLista.jsx`
  - Lista de transferencias com checkbox e valor aplicado.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/useTransferenciaHistoricoController.js`
  - Estado e handlers para abrir, carregar preview e confirmar baixa em lote.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/useEstoqueTransferenciaParceiroController.js`
  - Passar props novas para filtros/results.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaFilters.jsx`
  - Botao para abrir baixa por valor quando houver pessoa selecionada.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaResults.jsx`
  - Renderizar o painel de baixa por valor acima da lista.

## Tasks

### Task 1: Backend schemas and service distribution

**Files:**
- Create: `backend/app/estoque/transferencia_parceiro_baixa_lote_schemas.py`
- Create: `backend/app/estoque/transferencia_parceiro_baixa_lote_service.py`
- Test: `backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py`

- [ ] **Step 1: Write failing tests for money distribution**

Create tests for:

```python
def test_distribuir_valor_mais_antigo_primeiro_deixa_ultima_parcial():
    contas = [
        _conta(1, "2026-06-01", 400),
        _conta(2, "2026-06-02", 400),
        _conta(3, "2026-06-03", 400),
    ]
    resultado = distribuir_baixa_transferencias(contas, 1000, ordem="antiga")
    assert [(item["conta_receber_id"], item["valor_baixado"]) for item in resultado] == [
        (1, Decimal("400.00")),
        (2, Decimal("400.00")),
        (3, Decimal("200.00")),
    ]
```

- [ ] **Step 2: Verify the tests fail**

Run:

```powershell
python -m pytest backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py -q
```

Expected: import failure because the new service does not exist yet.

- [ ] **Step 3: Implement schemas and distribution helpers**

Add Pydantic models for preview/confirmacao and implement:

```python
def distribuir_baixa_transferencias(contas, valor_total, *, ordem="antiga") -> list[dict]:
    ...
```

- [ ] **Step 4: Verify distribution tests pass**

Run:

```powershell
python -m pytest backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py -q
```

Expected: distribution tests pass.

### Task 2: Backend apply and routes

**Files:**
- Modify: `backend/app/estoque/transferencia_parceiro_baixa_lote_service.py`
- Create: `backend/app/estoque/transferencia_parceiro_baixa_lote_routes.py`
- Modify: `backend/app/estoque_transferencia_parceiro_routes.py`
- Modify: `backend/tests/unit/test_estoque_transferencia_parceiro_routes_contract.py`
- Test: `backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py`

- [ ] **Step 1: Add failing tests for route registration and apply validation**

Test route paths:

```python
assert ("/estoque/transferencia-parceiro/baixa-lote/preview", "POST") in routes
assert ("/estoque/transferencia-parceiro/baixa-lote", "POST") in routes
```

Test validation:

```python
def test_produto_devolvido_com_estoque_rejeita_baixa_parcial():
    with pytest.raises(HTTPException):
        validar_devolucao_estoque_integral(conta_com_saldo_400, Decimal("200.00"))
```

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
python -m pytest backend/tests/unit/test_estoque_transferencia_parceiro_routes_contract.py backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py -q
```

Expected: new route assertions fail.

- [ ] **Step 3: Implement apply service and routes**

Implement preview and confirmation endpoints. Confirmation must update `ContaReceber`, create `Recebimento` for financial/acerto, create `Pagamento` for acerto compensation, optionally create estoque estorno for full product return, and create a `LancamentoManual` for financial receipts.

- [ ] **Step 4: Verify backend focused tests pass**

Run:

```powershell
python -m pytest backend/tests/unit/test_estoque_transferencia_parceiro_routes_contract.py backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py -q
```

Expected: all focused backend tests pass.

### Task 3: Frontend helpers and panel

**Files:**
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.js`
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs`
- Create: `frontend/src/pages/estoqueTransferenciaParceiro/BaixaLoteTransferenciaPanel.jsx`
- Create: `frontend/src/pages/estoqueTransferenciaParceiro/BaixaLoteTransferenciaLista.jsx`

- [ ] **Step 1: Write failing frontend helper tests**

Add tests for `distribuirBaixaTransferencias`:

```javascript
assert.deepEqual(distribuirBaixaTransferencias("1000", registros, "antiga"), {
  1: "400.00",
  2: "400.00",
  3: "200.00",
});
```

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
node frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs
```

Expected: missing export failure.

- [ ] **Step 3: Implement helper and small components**

Keep each new component focused: panel owns form layout; list owns checkbox/value rows.

- [ ] **Step 4: Verify frontend helper tests pass**

Run:

```powershell
node frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs
```

Expected: all tests pass.

### Task 4: Frontend integration and final verification

**Files:**
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/useTransferenciaHistoricoController.js`
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/useEstoqueTransferenciaParceiroController.js`
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaFilters.jsx`
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaResults.jsx`

- [ ] **Step 1: Add controller state and API calls**

Controller should expose `baixaLoteTransferencia`, `abrirBaixaLoteTransferencia`, `fecharBaixaLoteTransferencia`, `carregarPreviewBaixaLoteTransferencia`, `registrarBaixaLoteTransferencia`.

- [ ] **Step 2: Add UI entry points**

Filters render "Baixa por valor" when a pessoa is selected. Results render the panel when open.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest backend/tests/unit/test_estoque_transferencia_parceiro_routes_contract.py backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py -q
node frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs
```

Expected: all focused tests pass.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: build exits 0.

## Self-Review

Spec coverage:

- baixa por valor com sugestao automatica: Tasks 1, 3, 4;
- checkbox e revisao: Tasks 3, 4;
- recebimento financeiro: Task 2;
- acerto/compensacao: Task 2;
- produto devolvido com estoque opcional: Task 2;
- arquivos pequenos: File Structure and Tasks 2-4;
- campo valor lancado diferente do custo fora desta fase: no task includes it.

Placeholder scan: no `TODO`, `TBD` or undefined task remains.

Type consistency: backend uses `conta_receber_id`, `valor_baixado`, `modo_baixa`, `forma_pagamento_id`, `devolver_estoque`; frontend payload mirrors those names.
