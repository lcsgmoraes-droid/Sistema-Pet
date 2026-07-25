from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bling_cost_sync_contract_is_registered_end_to_end():
    catalog = read_text("backend/app/bling_integration_parts/catalogo.py")
    models = read_text("backend/app/produtos_estoque_models.py")
    db_init = read_text("backend/app/db/__init__.py")
    scheduler = read_text("backend/app/schedulers/bling_sync_scheduler.py")
    routes = read_text("backend/app/bling_sync_routes.py")
    cost_routes = read_text("backend/app/bling_sync/custos_routes.py")

    assert "def listar_produtos_fornecedores" in catalog
    assert "def atualizar_produto_fornecedor" in catalog
    assert "class ProdutoBlingCostSyncQueue" in models
    assert "bling_cost_sync_events" in db_init
    assert "BlingCostSyncService.process_pending_queue" in scheduler
    assert "router.include_router(custos_bling_router)" in routes
    assert '@router.post("/custos-bling/marca")' in cost_routes


def test_bling_cost_migration_follows_current_head_and_enables_rls():
    migration = read_text(
        "backend/alembic/versions/zwm20260724a1_bling_cost_sync_queue.py"
    )

    assert 'revision = "zwm20260724a1"' in migration
    assert 'down_revision = "zwl20260723a1"' in migration
    assert "apply_tenant_rls" in migration
    assert "uq_produto_bling_cost_sync_tenant_produto" in migration
