from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zws20260803a1_nfse_focus_pilot_foundation.py"
)
FISCAL_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zwt20260803a1_nfse_company_fiscal_parameters.py"
)


def test_nfse_migration_has_single_expected_parent_and_rls():
    content = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "zws20260803a1"' in content
    assert 'down_revision = "zwr20260801a1"' in content
    assert 'TABLES = ("nfse_tenant_configs", "nfse_documents")' in content
    assert "apply_tenant_rls(" in content


def test_nfse_tables_are_tracked_by_raw_sql_tenant_guard():
    from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES

    assert {"nfse_tenant_configs", "nfse_documents"} <= TENANT_SCOPED_TABLES


def test_nfse_fiscal_parameters_extend_the_existing_tenant_scoped_company_config():
    content = FISCAL_MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "zwt20260803a1"' in content
    assert 'down_revision = "zws20260803a1"' in content
    assert '"empresa_config_fiscal"' in content
    assert '"nfse_item_lista_servico"' in content
    assert '"municipio_iss_codigo"' in content
