# Catalogo Base Administrativo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable administrative import that copies Lucas's base product catalog into a tenant with prices, costs, suppliers and stock reset.

**Architecture:** Add a backend service that reads a source tenant, remaps catalog support records into the target tenant, copies products/images with sanitized operational fields, and records item-level idempotency in existing template install tables. Add a CLI script for dry-run/apply so support can run this for any new tenant before a UI exists.

**Tech Stack:** Python, SQLAlchemy, existing multitenant models, existing template install audit tables, pytest.

---

### Task 1: Service Contract And Result Model

**Files:**
- Create: `backend/app/services/base_catalog_import_service.py`
- Test: `backend/tests/multi_tenant/test_base_catalog_import_service.py`

- [ ] **Step 1: Write failing tests for dry-run and sanitization**

Create a SQLite fixture with `tenants`, `users`, `template` audit tables, `departamentos`, `categorias`, `marcas`, option tables, `produtos`, `produto_imagens`, `produto_kit_componentes`, and `produto_granel_vinculos`. Seed a source tenant with one department, one category, one brand, one product with stock/cost/price/supplier, and one image row.

Expected dry-run:

```python
result = import_base_catalog(
    db=session,
    source_tenant_id=SOURCE_TENANT,
    target_tenant_id=TARGET_TENANT,
    user_id=10,
    dry_run=True,
)

assert result["dry_run"] is True
assert result["would_create"]["departamentos"] == 1
assert result["would_create"]["categorias"] == 1
assert result["would_create"]["marcas"] == 1
assert result["would_create"]["produtos"] == 1
assert count(session, "produtos", TARGET_TENANT) == 0
```

Expected apply:

```python
result = import_base_catalog(
    db=session,
    source_tenant_id=SOURCE_TENANT,
    target_tenant_id=TARGET_TENANT,
    user_id=10,
    dry_run=False,
)

product = one_target_product(session)
assert product["estoque_atual"] == 0
assert product["estoque_fisico"] == 0
assert product["estoque_ecommerce"] == 0
assert product["estoque_minimo"] == 0
assert product["estoque_maximo"] == 0
assert product["preco_custo"] == 0
assert product["preco_venda"] == 0
assert product["preco_promocional"] is None
assert product["preco_app"] is None
assert product["preco_ecommerce"] is None
assert product["fornecedor_id"] is None
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_service.py -q
```

Expected: import error for missing `app.services.base_catalog_import_service`.

- [ ] **Step 3: Implement service result helpers**

Create `BaseCatalogImportResult` with buckets `created`, `skipped`, `would_create`, `warnings`, `errors`, and `to_dict()`.

- [ ] **Step 4: Implement tenant guards**

Validate:

```python
if str(source_tenant_id) == str(target_tenant_id):
    raise BaseCatalogImportError("Tenant fonte e destino nao podem ser iguais.")
```

Validate both tenants exist when the `tenants` table is present.

- [ ] **Step 5: Run service tests**

Run the same pytest command. Expected: dry-run and sanitization tests pass.

### Task 2: Copy Support Catalogs

**Files:**
- Modify: `backend/app/services/base_catalog_import_service.py`
- Test: `backend/tests/multi_tenant/test_base_catalog_import_service.py`

- [ ] **Step 1: Write failing test for support records**

Seed source departments, parent/child categories, brand, and ration option tables. Apply import. Assert target categories preserve parent and department mapping, and product points to target IDs, not source IDs.

- [ ] **Step 2: Verify failing test**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_service.py::test_import_remaps_catalog_support_records -q
```

Expected: FAIL because remapping is not implemented.

- [ ] **Step 3: Implement remap helpers**

Implement reusable helpers:

```python
def _template_code(item_type: str, source_id: int) -> str:
    return f"{item_type}:{source_id}"
```

Use `tenant_template_item_installs` to find prior target IDs before creating records.

- [ ] **Step 4: Implement department/category/brand/options copy**

Copy records tenant-scoped into target. For categories, do two passes: create categories without parent first, then update `categoria_pai_id` using the source-to-target map.

- [ ] **Step 5: Run service tests**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_service.py -q
```

Expected: support remapping tests pass.

### Task 3: Copy Products, Images, And Product Relations

**Files:**
- Modify: `backend/app/services/base_catalog_import_service.py`
- Test: `backend/tests/multi_tenant/test_base_catalog_import_service.py`

- [ ] **Step 1: Write failing test for product relations**

Seed source parent/product variation, predecessor relation, kit component, granel relation, and image rows. Apply import. Assert target relations point only to target product IDs and imported image URLs do not contain the source tenant ID.

- [ ] **Step 2: Verify failing test**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_service.py::test_import_remaps_product_relations_and_images -q
```

Expected: FAIL because relations/images are not implemented.

- [ ] **Step 3: Implement product copy**

Copy product scalar fields but force operational fields to zero/null according to the spec. Preserve category, department, brand and product taxonomy fields using maps.

- [ ] **Step 4: Implement relation remap**

After all products are created, update target product references:

- `produto_pai_id`;
- `produto_predecessor_id`;
- `produto_kit_componentes.kit_id`;
- `produto_kit_componentes.produto_componente_id`;
- `produto_granel_vinculos.produto_origem_id`;
- `produto_granel_vinculos.produto_granel_id`.

- [ ] **Step 5: Implement image copy abstraction**

For the first version, keep image database rows copied and URLs rewritten through a helper. In production S3, the helper copies object keys; in tests, use a no-op copier that returns rewritten URLs.

- [ ] **Step 6: Run service tests**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_service.py -q
```

Expected: all service tests pass.

### Task 4: Administrative CLI

**Files:**
- Create: `backend/app/scripts/run_base_catalog_import.py`
- Test: `backend/tests/multi_tenant/test_base_catalog_import_script.py`

- [ ] **Step 1: Write failing CLI tests**

Test that the script defaults to dry-run and rejects `--apply` in production without `--allow-production-apply`.

- [ ] **Step 2: Verify failing test**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_script.py -q
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: Implement CLI**

Arguments:

```text
--target-tenant-id
--target-user-id
--source-email admin@mlprohub.com.br
--apply
--allow-production-apply
```

Resolve source tenant by `users.email`, call service, commit on apply and rollback on dry-run.

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_script.py -q
```

Expected: CLI tests pass.

### Task 5: Verification And Finish

**Files:**
- Modify: `docs/CONTRATO_MULTITENANT_E_ONBOARDING.md`

- [ ] **Step 1: Document administrative catalog import**

Add a short section saying product catalog import is explicit/admin-only, copies support catalogs/products/images, and sanitizes stock/cost/price/suppliers.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
cd backend; pytest tests/multi_tenant/test_base_catalog_import_service.py tests/multi_tenant/test_base_catalog_import_script.py tests/multi_tenant/test_phase3_tenant_onboarding_service.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run git status**

Run:

```powershell
git status --short --branch
```

Expected: only intended files changed.
