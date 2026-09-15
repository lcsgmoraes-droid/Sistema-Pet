from pathlib import Path

from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic" / "versions" / "ifs20260819a1_nfse_manual_assistida.py"


def test_nfse_manual_migration_is_linear_and_tenant_scoped():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "ifs20260819a1"' in source
    assert 'down_revision = "ifr20260816a1"' in source
    assert 'TABLES = ("nfse_manual_documents",)' in source
    assert "apply_tenant_rls" in source
    assert (
        'sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False)'
        in source
    )
    assert "uq_nfse_manual_documents_tenant_ref" in source
    assert "uq_nfse_manual_documents_tenant_invoice" in source
    assert "ck_nfse_manual_documents_status" in source


def test_nfse_manual_table_is_registered_as_tenant_scoped():
    assert "nfse_manual_documents" in TENANT_SCOPED_TABLES


def test_nfse_manual_routes_filter_documents_by_tenant():
    routes = (ROOT / "app" / "nfse_manual" / "routes.py").read_text(encoding="utf-8")

    assert "NfseManualDocument.tenant_id == tenant_id" in routes
    assert "ConsultaVet.tenant_id == tenant_id" in routes
    assert "Cliente.tenant_id == tenant_id" in routes
