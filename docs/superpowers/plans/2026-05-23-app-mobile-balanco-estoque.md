# App Mobile Balanco de Estoque por Camera Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the employee mobile stock balance flow where the employee scans or searches ERP products, enters the final counted stock, and the backend records the required inventory adjustment.

**Architecture:** Add operational employee profile support to the existing mobile auth flow, expose focused `/app/funcionario/estoque` backend endpoints, and add a dedicated mobile navigator/screen/service for stock balance. Backend endpoints reuse the existing ERP stock movement semantics: positive difference creates entry, negative difference creates exit, zero difference creates no movement.

**Tech Stack:** FastAPI, SQLAlchemy, pytest contract tests, Expo React Native, TypeScript, Zustand auth store, `expo-camera`.

---

## Files

- Modify: `backend/app/routes/ecommerce_auth.py`
  - Add `funcionario` operational profile detection.
- Modify: `backend/app/routes/app_mobile_routes.py`
  - Add employee stock product search, barcode lookup, and balance endpoints.
- Add: `backend/tests/unit/test_app_mobile_funcionario_estoque_contract.py`
  - Source-level and behavior contract checks for the new endpoints.
- Modify: `app-mobile/src/types/index.ts`
  - Add employee operational flags and stock balance types.
- Modify: `app-mobile/src/store/auth.store.ts`
  - Cache employee operational role.
- Modify: `app-mobile/src/navigation/AppNavigator.tsx`
  - Route employee users to the new navigator.
- Add: `app-mobile/src/types/funcionarioNavigation.ts`
  - Navigation param list for employee area.
- Add: `app-mobile/src/navigation/FuncionarioNavigator.tsx`
  - Operational tab/stack for employee.
- Add: `app-mobile/src/services/funcionarioEstoque.service.ts`
  - API calls for ERP product search and balance.
- Add: `app-mobile/src/screens/funcionario/FuncionarioBalancoScreen.tsx`
  - Camera/search/form screen.

---

### Task 1: Backend Contract Tests

**Files:**
- Add: `backend/tests/unit/test_app_mobile_funcionario_estoque_contract.py`

- [ ] **Step 1: Write failing source contract tests**

Create tests that assert the backend exposes `/app/funcionario/estoque`, does not reuse the public app catalog filter `anunciar_app`, and includes balance behavior for entrada, saida and zero difference.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_app_mobile_funcionario_estoque_contract.py -q`

Expected: FAIL because the new routes and profile strings do not exist yet.

### Task 2: Employee Profile Detection

**Files:**
- Modify: `backend/app/routes/ecommerce_auth.py`
- Modify: `app-mobile/src/types/index.ts`
- Modify: `app-mobile/src/store/auth.store.ts`

- [ ] **Step 1: Extend backend profile serialization**

In `_serialize_profile`, detect active ERP employees with `cliente.tipo_cadastro == "funcionario"` and return:

```python
"is_funcionario": is_funcionario,
"funcionario_id": cliente.id if (cliente and (is_entregador or is_funcionario)) else None,
"perfil_operacional": perfil_operacional,
```

Priority order: veterinario, entregador, funcionario, cliente.

- [ ] **Step 2: Extend mobile user types and cache**

Add `is_funcionario?: boolean` and extend `perfil_operacional` union with `"funcionario"`. Cache and restore `is_funcionario` the same way as veterinarian/delivery roles.

- [ ] **Step 3: Run profile contract tests**

Run: `pytest backend/tests/unit/test_app_mobile_funcionario_estoque_contract.py -q`

Expected: backend contract checks for profile strings pass after route implementation in Task 3.

### Task 3: Backend Employee Stock Endpoints

**Files:**
- Modify: `backend/app/routes/app_mobile_routes.py`

- [ ] **Step 1: Add response/request schemas**

Add focused schemas:

```python
class FuncionarioProdutoEstoqueResponse(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    sku: Optional[str] = None
    codigo_barras: Optional[str] = None
    unidade: str
    preco_venda: float
    preco_custo: Optional[float] = None
    estoque_atual: float
    is_parent: bool = False
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None

class FuncionarioBalancoRequest(BaseModel):
    produto_id: int
    saldo_final: float
    numero_lote: Optional[str] = None
    data_validade: Optional[str] = None
    observacao: Optional[str] = None
```

- [ ] **Step 2: Add employee authorization helper**

Add helper that uses current mobile user and tenant, loads linked `Cliente`, and requires `tipo_cadastro == "funcionario"` or an accepted operational flag. Return `(cliente, tenant_id)`.

- [ ] **Step 3: Add ERP product query helper**

Search `Produto` by tenant, active status, code/SKU/barcode/GTIN/alternative codes/name. Do not require `Produto.anunciar_app == True`.

- [ ] **Step 4: Add balance endpoint**

Calculate `diferenca = saldo_final - estoque_atual`; call existing stock logic semantically by creating the same movements as `/estoque/entrada` and `/estoque/saida` do, with `motivo="balanco"` and observation starting with `App funcionario - balanco por camera`.

- [ ] **Step 5: Run backend contract tests**

Run: `pytest backend/tests/unit/test_app_mobile_funcionario_estoque_contract.py backend/tests/unit/test_app_mobile_barcode_contract.py -q`

Expected: PASS.

### Task 4: Mobile Navigation and Service

**Files:**
- Add: `app-mobile/src/types/funcionarioNavigation.ts`
- Add: `app-mobile/src/navigation/FuncionarioNavigator.tsx`
- Modify: `app-mobile/src/navigation/AppNavigator.tsx`
- Add: `app-mobile/src/services/funcionarioEstoque.service.ts`

- [ ] **Step 1: Add navigator and route type**

Create a simple stack with `FuncionarioBalanco` as the first screen and a logout action matching the existing operational navigators.

- [ ] **Step 2: Route employee users**

In `AppNavigator`, route users with `is_funcionario` or `perfil_operacional === "funcionario"` to `FuncionarioNavigator`.

- [ ] **Step 3: Add API service**

Implement:

```ts
buscarProdutoFuncionarioPorBarcode(barcode: string)
buscarProdutosFuncionario(q: string)
registrarBalancoFuncionario(payload)
```

Use `/app/funcionario/estoque/produtos/barcode/{barcode}`, `/app/funcionario/estoque/produtos/buscar`, and `/app/funcionario/estoque/balanco`.

### Task 5: Mobile Balance Screen

**Files:**
- Add: `app-mobile/src/screens/funcionario/FuncionarioBalancoScreen.tsx`

- [ ] **Step 1: Build scanner/search layout**

Use `CameraView` for scanning, manual search input, and a product result card. Product card shows name, code, price, cost, stock and unit.

- [ ] **Step 2: Build final stock form**

Add fields for final counted stock, lot number, validity date and notes. Show calculated difference before saving.

- [ ] **Step 3: Save and keep session history**

Call `registrarBalancoFuncionario`, clear the form on success, update the displayed product stock, and append the result to an in-memory session history list.

- [ ] **Step 4: Handle invalid cases**

Show clear alerts for product not found, parent product, virtual kit, invalid stock and network failures.

### Task 6: Verification

**Files:**
- Backend and app files from previous tasks.

- [ ] **Step 1: Run backend focused tests**

Run: `pytest backend/tests/unit/test_app_mobile_funcionario_estoque_contract.py backend/tests/unit/test_app_mobile_barcode_contract.py -q`

Expected: PASS.

- [ ] **Step 2: Run mobile typecheck**

Run: `npm --prefix app-mobile run typecheck`

Expected: PASS.

- [ ] **Step 3: Inspect diff**

Run: `git diff --check`

Expected: no whitespace errors.

