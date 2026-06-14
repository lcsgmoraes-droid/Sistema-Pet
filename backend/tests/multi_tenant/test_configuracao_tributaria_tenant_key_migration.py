from pathlib import Path
from types import SimpleNamespace

from tests.multi_tenant.rls_migration_helpers import load_migration


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "tp20260614a1_configuracao_tributaria_tenant_key.py"
)


def _load_migration():
    return load_migration(MIGRATION_PATH)


def _capture_migration(monkeypatch, action: str, *, dialect="postgresql"):
    migration = _load_migration()
    emitted = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))

    fake_op = SimpleNamespace(
        get_bind=lambda: bind,
        execute=lambda sql: emitted.append(("execute", str(sql))),
        create_unique_constraint=lambda name, table, columns: emitted.append(
            ("create_unique_constraint", name, table, tuple(columns))
        ),
        drop_constraint=lambda name, table, type_=None: emitted.append(
            ("drop_constraint", name, table, type_)
        ),
    )
    monkeypatch.setitem(migration[action].__globals__, "op", fake_op)
    migration[action]()
    return emitted


def test_configuracao_tributaria_tenant_key_migration_metadata():
    migration = _load_migration()

    assert migration["revision"] == "tp20260614a1"
    assert migration["down_revision"] == "to20260614a1"
    assert migration["CONFIGURACAO_TRIBUTARIA_TABLE"] == "configuracao_tributaria"
    assert migration["LEGACY_USUARIO_UNIQUE"] == "configuracao_tributaria_usuario_id_key"
    assert migration["TENANT_UNIQUE"] == "uq_configuracao_tributaria_tenant_id"


def test_upgrade_troca_usuario_global_por_tenant_unico(monkeypatch):
    emitted = _capture_migration(monkeypatch, "upgrade")

    assert (
        "execute",
        "ALTER TABLE configuracao_tributaria "
        "DROP CONSTRAINT IF EXISTS configuracao_tributaria_usuario_id_key",
    ) in emitted
    assert (
        "create_unique_constraint",
        "uq_configuracao_tributaria_tenant_id",
        "configuracao_tributaria",
        ("tenant_id",),
    ) in emitted


def test_downgrade_recria_usuario_global_unico(monkeypatch):
    emitted = _capture_migration(monkeypatch, "downgrade")

    assert (
        "drop_constraint",
        "uq_configuracao_tributaria_tenant_id",
        "configuracao_tributaria",
        "unique",
    ) in emitted
    assert (
        "create_unique_constraint",
        "configuracao_tributaria_usuario_id_key",
        "configuracao_tributaria",
        ("usuario_id",),
    ) in emitted


def test_migration_nao_roda_fora_de_postgresql(monkeypatch):
    assert _capture_migration(monkeypatch, "upgrade", dialect="sqlite") == []
    assert _capture_migration(monkeypatch, "downgrade", dialect="sqlite") == []
