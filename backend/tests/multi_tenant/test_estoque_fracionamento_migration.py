from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import load_migration, migration_path


MIGRATION_FILE = migration_path("zzc20260903a1_fracionamento_clinico.py")
TABLES = (
    "estoque_fracionamento_vinculos",
    "estoque_fracionamento_conversoes",
)


def test_migration_cria_tabelas_com_rls():
    migration = load_migration(MIGRATION_FILE)
    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert migration["revision"] == "zzf20260903a1"
    assert migration["down_revision"] == "zze20260903a1"
    assert migration["TABLES"] == TABLES
    assert "apply_tenant_rls(" in source
    assert "enable=True" in source
    assert "enable=False" in source


def test_tabelas_de_fracionamento_estao_nas_guardas_de_sql_bruto():
    for table_name in TABLES:
        assert table_name in TENANT_SCOPED_TABLES
        assert table_name in TENANT_TABLES
