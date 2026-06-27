from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2] / "app"


def _source(relative_path: str) -> str:
    return (APP_DIR / relative_path).read_text(encoding="utf-8")


def test_segmentacao_listar_segmentos_joins_clientes_with_tenant_safe_sql():
    source = _source("services/segmentacao_service.py")
    block = source.split("def listar_segmentos(", 1)[1]

    assert "execute_tenant_safe" in source
    assert "JOIN clientes c ON cs.cliente_id = c.id AND c.{tenant_filter}" in block
    assert "WHERE cs.{tenant_filter}" in block
    assert "tenant_id=tenant_id" in block
    assert "db.execute(" not in block


def test_commission_schema_backfill_syncs_rls_before_reading_clientes():
    source = _source("comissoes_schema_guard.py")
    block = source.split("def ensure_comissoes_config_schema(", 1)[1].split(
        "_comissoes_schema_checked = True", 1
    )[0]

    assert "get_current_tenant_id" in source
    assert "sync_rls_tenant" in source
    assert "tenant_id = get_current_tenant_id()" in block
    assert "sync_rls_tenant(db, tenant_id)" in block
    assert "c.tenant_id = :tenant_id" in block
    assert '{"tenant_id": str(tenant_id)}' in block
