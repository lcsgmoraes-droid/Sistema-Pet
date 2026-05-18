# Refinar Agenda Vet E Internacao Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refinar a agenda veterinaria no app e deixar a agenda de procedimentos da internacao mais clara, digitavel e correta no horario de Brasilia.

**Architecture:** O backend passa a tratar horarios escolhidos pelo usuario como horario de parede de Brasilia antes de persistir em colunas com timezone. O frontend web ganha um autocomplete clinico reutilizavel para medicamentos/procedimentos e labels mais claros. O app mobile amplia a agenda para dia, semana e mes usando o mesmo endpoint com intervalo de datas.

**Tech Stack:** FastAPI, SQLAlchemy, React/Vite, React Native/Expo, pytest, node:test.

---

### Task 1: Corrigir Contrato De Horario Da Internacao

**Files:**
- Modify: `backend/app/veterinario_core.py`
- Modify: `backend/app/veterinario_internacao_routes.py`
- Test: `backend/tests/unit/test_vet_core_timezone.py`

- [ ] Add a failing test proving that a naive `datetime(2026, 5, 18, 0, 2)` from a `datetime-local` input is stored as an aware Brasilia datetime, not as UTC midnight.
- [ ] Run the focused pytest command and confirm the new test fails before implementation.
- [ ] Add a helper in `veterinario_core.py` for user-entered wall-clock datetime values.
- [ ] Use that helper when creating and completing internacao procedure agenda items.
- [ ] Run the focused pytest command and confirm it passes.

### Task 2: Backend Agenda Mobile Com Intervalo

**Files:**
- Modify: `backend/app/routes/app_vet_routes.py`
- Test: `backend/tests/unit/test_app_vet_routes_contract.py`

- [ ] Add a route-contract test asserting `/app/vet/agendamentos` accepts optional `data_inicio` and `data_fim` query params without removing the existing `data` param.
- [ ] Update `listar_agendamentos_vet_mobile` so `data` keeps the old behavior and `data_inicio/data_fim` returns a date range.
- [ ] Keep ordering by `data_hora.asc()`.
- [ ] Run the focused backend tests.

### Task 3: Web Autocomplete Clinico Reutilizavel

**Files:**
- Create: `frontend/src/components/veterinario/CatalogoClinicoAutocomplete.jsx`
- Modify: `frontend/src/pages/veterinario/internacoes/AgendaProcedimentoForm.jsx`
- Test: `frontend/src/components/veterinario/catalogoClinicoAutocompleteUtils.test.mjs`
- Create: `frontend/src/components/veterinario/catalogoClinicoAutocompleteUtils.js`

- [ ] Add filtering utility tests for typed searches across medication/procedure name, active ingredient, description, and type.
- [ ] Implement the utility.
- [ ] Create the component with free typing, suggestion list, selected-item metadata, and optional `+ Novo` action.
- [ ] Replace the select plus duplicated chosen-name field in `AgendaProcedimentoForm`.
- [ ] Keep manual text entry supported when the item is not in the catalog.

### Task 4: Labels E Ajuda Da Agenda De Procedimentos

**Files:**
- Modify: `frontend/src/pages/veterinario/internacoes/AgendaProcedimentoForm.jsx`
- Modify: `frontend/src/pages/veterinario/internacoes/AgendaProcedimentoCard.jsx`

- [ ] Rename fields to patient-friendly clinical wording: dose indicada/orientacao clinica, quantidade por aplicacao, unidade, via de administracao.
- [ ] Add concise helper text/tooltips that explain dose reference vs quantity applied.
- [ ] Avoid showing the selected medication/procedure twice.
- [ ] Keep the agenda card display aligned with the same language.

### Task 5: App Mobile Agenda Dia/Semana/Mes

**Files:**
- Modify: `app-mobile/src/services/vet.service.ts`
- Modify: `app-mobile/src/screens/veterinario/VetAgendaScreen.tsx`

- [ ] Extend `listarAgendamentosVet` to accept `data`, `data_inicio`, and `data_fim`.
- [ ] Add local date helpers in the screen for day/week/month ranges.
- [ ] Add segmented controls for `Dia`, `Semana`, and `Mes`.
- [ ] Group agenda cards by day for week/month views.
- [ ] Preserve pull-to-refresh and empty states.

### Task 6: Validacao E Publicacao

**Files:**
- No code files expected.

- [ ] Run backend focused tests.
- [ ] Run frontend build.
- [ ] Run app-mobile typecheck.
- [ ] Run `git diff --check`.
- [ ] Finish with `scripts/git_finish_task.ps1 -Mensagem "feat: refinar agenda veterinaria" -Push`.
- [ ] Open a Pull Request and only deploy after explicit approval.
