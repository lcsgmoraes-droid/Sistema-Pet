# Extrato e Faturamento Veterinario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** entregar o MVP de extrato realizado do atendimento veterinario, com JSON, PDF, Excel e painel de exportacao.

**Architecture:** calculos puros ficam em `veterinario_extratos.py`; rotas carregam dados do tenant e chamam os helpers; a UI reutiliza o formato de colunas para selecionar exportacoes. O extrato diferencia linhas contabilizaveis de linhas de detalhe para evitar duplicidade entre procedimento e seus insumos.

**Tech Stack:** FastAPI, SQLAlchemy, openpyxl, reportlab, React/Vite, Node test runner.

---

### Task 1: Backend Helper e Contrato

**Files:**
- Create: `backend/app/veterinario_extratos.py`
- Create: `backend/tests/unit/test_vet_extratos_mvp.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_extrato_contabiliza_procedimento_e_detalha_insumos_sem_duplicar():
    produto = {"id": 10, "codigo": "DEF", "nome": "Defenza", "preco_venda": 40, "unidade": "un"}
    procedimento = {"id": 5, "nome": "Consulta", "valor": 120, "insumos": [{"produto_id": 10, "quantidade": 1, "custo_unitario": 25, "custo_total": 25}]}
    extrato = montar_extrato_atendimento(procedimentos_consulta=[procedimento], produtos_por_id={10: produto})
    assert extrato["totais"]["preco_total"] == 120
    assert extrato["totais"]["custo_total"] == 25
    assert len(extrato["linhas"]) == 2
```

- [ ] **Step 2: Run RED**

Run: `.\\backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/unit/test_vet_extratos_mvp.py -q`
Expected: fail because `app.veterinario_extratos` does not exist yet.

- [ ] **Step 3: Implement minimal helper**

Add column metadata, line builders, totals and document byte generation in `backend/app/veterinario_extratos.py`.

- [ ] **Step 4: Run GREEN**

Run: `.\\backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/unit/test_vet_extratos_mvp.py -q`
Expected: pass.

### Task 2: API Routes

**Files:**
- Create: `backend/app/veterinario_extratos_routes.py`
- Modify: `backend/app/veterinario_routes.py`
- Modify: `backend/tests/unit/test_vet_extratos_mvp.py`

- [ ] **Step 1: Add failing route contract test**

```python
def test_rotas_de_extrato_veterinario_estao_registradas():
    from app.veterinario_routes import router
    routes = {(route.path, ",".join(sorted(route.methods))) for route in router.routes}
    assert ("/vet/extratos/atendimento", "GET") in routes
    assert ("/vet/extratos/atendimento/export.pdf", "GET") in routes
    assert ("/vet/extratos/atendimento/export.xlsx", "GET") in routes
```

- [ ] **Step 2: Run RED**

Run: `.\\backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/unit/test_vet_extratos_mvp.py -q`
Expected: route assertions fail.

- [ ] **Step 3: Implement routes**

Create the router, load consulta/internacao with tenant filters, call helper, and return `StreamingResponse` for PDF/XLSX.

- [ ] **Step 4: Run GREEN**

Run: `.\\backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/unit/test_vet_extratos_mvp.py -q`
Expected: pass.

### Task 3: Frontend Panel

**Files:**
- Create: `frontend/src/pages/veterinario/extratos/extratoUtils.js`
- Create: `frontend/src/pages/veterinario/extratos/extratoUtils.test.mjs`
- Create: `frontend/src/pages/veterinario/extratos/ExtratoAtendimentoPanel.jsx`
- Modify: `frontend/src/pages/veterinario/vetApi.js`
- Modify: `frontend/src/pages/veterinario/VetConsultaForm.jsx`
- Modify: `frontend/src/pages/veterinario/internacoes/InternacaoDetalhe.jsx`

- [ ] **Step 1: Write failing frontend tests**

```javascript
import assert from "node:assert/strict";
import { test } from "node:test";
import { normalizarColunasSelecionadas } from "./extratoUtils.js";

test("normaliza colunas validas sem duplicar", () => {
  assert.deepEqual(normalizarColunasSelecionadas(["nome", "nome", "preco_total", "x"]), ["nome", "preco_total"]);
});
```

- [ ] **Step 2: Run RED**

Run: `node --test frontend/src/pages/veterinario/extratos/extratoUtils.test.mjs`
Expected: fail because util does not exist.

- [ ] **Step 3: Implement UI**

Add the panel with resumo, table, checkboxes and buttons for PDF/XLSX downloads.

- [ ] **Step 4: Run GREEN and build**

Run: `node --test frontend/src/pages/veterinario/extratos/extratoUtils.test.mjs`
Run: `npm run build` in `frontend`
Expected: both pass.

### Task 4: Final Verification

**Files:**
- Verify changed backend/frontend files.

- [ ] **Step 1: Run focused backend tests**

Run: `.\\backend\\.venv\\Scripts\\python.exe -m pytest backend/tests/unit/test_vet_extratos_mvp.py backend/tests/unit/test_vet_orcamentos_mvp.py -q`
Expected: all pass.

- [ ] **Step 2: Run release-check**

Run: `.\\FLUXO_UNICO.bat release-check`
Expected: release-check passes on feature branch.

- [ ] **Step 3: Finish task**

Run: `powershell -ExecutionPolicy Bypass -File .\\scripts\\git_finish_task.ps1 -Mensagem "feat: adicionar extrato veterinario" -Push`
Expected: branch pushed and ready for pull request.
