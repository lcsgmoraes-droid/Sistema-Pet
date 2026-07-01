# Transferencia Parceiro Acerto Direto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o usuario crie uma nova conta a pagar de acerto dentro da baixa por valor de transferencia parceiro e compense essa divida na mesma confirmacao.

**Architecture:** A baixa por valor continua sendo o ponto de entrada. O backend recebe um payload opcional `nova_conta_pagar_acerto`, cria a conta a pagar vinculada ao parceiro e a inclui na compensacao do acerto. O frontend adiciona uma pequena secao no painel de baixa por valor, mantendo helpers e controller separados para nao inflar arquivos.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, React, Vite, node:test.

---

## File Structure

- Modify: `backend/app/estoque/transferencia_parceiro_baixa_lote_schemas.py`
  - Adicionar schema da nova conta a pagar do acerto.
- Modify: `backend/app/estoque/transferencia_parceiro_baixa_lote_service.py`
  - Criar a conta a pagar quando enviada e compensar junto com contas existentes.
- Modify: `backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py`
  - Cobrir validacao e criacao da conta direta em memoria/fake session.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.js`
  - Normalizar `nova_conta_pagar_acerto` no payload.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs`
  - Cobrir payload de acerto com nova conta a pagar.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/useTransferenciaBaixaLoteController.js`
  - Validar total compensado somando contas existentes e nova conta.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/BaixaLoteTransferenciaPanel.jsx`
  - Mostrar botao/area "Lancar divida para acerto" no modo acerto.
- Modify: `frontend/src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaFilters.jsx`
  - Renomear/realcar o botao para "Registrar acerto" quando houver pessoa selecionada.

## Tasks

### Task 1: Backend schema and service

- [ ] Add `TransferenciaParceiroNovaContaPagarAcertoRequest` with `descricao`, `valor`, `data_vencimento`, `documento`, `observacao`, `categoria_id`, `dre_subcategoria_id`, `tipo_despesa_id`.
- [ ] Add `nova_conta_pagar_acerto` to `TransferenciaParceiroBaixaLoteRequest`.
- [ ] Add helper `criar_conta_pagar_acerto_lote(...)` that creates `ContaPagar` with `status="pendente"`, `valor_pago=0`, `valor_original=valor`, `valor_final=valor`, `fornecedor_id=parceiro_id`, `canal="transferencia_parceiro"`, and an audit observation.
- [ ] In `aplicar_compensacoes_acerto_lote`, include the created conta ID in the list of compensation items.
- [ ] Reject `nova_conta_pagar_acerto` outside `modo_baixa="acerto"`.
- [ ] Run `python -m pytest backend/tests/unit/test_transferencia_parceiro_baixa_lote_service.py -q`.

### Task 2: Frontend payload and controller

- [ ] Extend `criarFormBaixaTransferencia` defaults with `nova_conta_pagar_acerto` fields.
- [ ] Extend `montarBaixaLoteTransferenciaPayload` to include `nova_conta_pagar_acerto` only when mode is `acerto` and value is greater than zero.
- [ ] In the controller, validate that selected existing compensation plus new account value equals the applied transfer value.
- [ ] Run `node frontend/src/pages/estoqueTransferenciaParceiro/transferenciaParceiroUtils.test.mjs`.

### Task 3: UI in baixa por valor panel

- [ ] Rename the historical action button to "Registrar acerto" while keeping the same handler.
- [ ] In acerto mode, add a compact section "Lancar divida para acerto" with description, value, due date, document and observation.
- [ ] Show the total including existing compensations plus the new account value.
- [ ] Keep `BaixaLoteTransferenciaPanel.jsx` below 350 lines; if it grows too much, extract a small child component.
- [ ] Run `npm run build` in `frontend`.

### Task 4: Final verification and publish

- [ ] Run backend focused tests.
- [ ] Run frontend helper tests.
- [ ] Run frontend build.
- [ ] Run `git diff --check` for changed files.
- [ ] Commit only the files from this feature and push the branch.

## Self-Review

- Scope is limited to acerto direct account creation inside baixa por valor.
- Does not implement borrowed-product incoming stock flow.
- Does not implement valor lancado different from cost.
- Uses existing `ContaPagar`, `Pagamento`, and `FormaPagamento Acerto` patterns.
