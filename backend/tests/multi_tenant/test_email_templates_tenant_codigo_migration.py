from pathlib import Path
from types import SimpleNamespace

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.models import EmailTemplate
from tests.multi_tenant.rls_migration_helpers import load_migration


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "tm20260614a1_email_templates_tenant_codigo.py"
)


def _load_migration():
    return load_migration(MIGRATION_PATH)


def _run_migration(migration, engine, action):
    with engine.begin() as connection:
        fake_op = SimpleNamespace(
            get_bind=lambda: connection,
            execute=connection.execute,
            create_index=lambda name, table, columns, unique=False: connection.execute(
                text(
                    f"CREATE {'UNIQUE ' if unique else ''}INDEX {name} "
                    f"ON {table} ({', '.join(columns)})"
                )
            ),
            drop_index=lambda name, table_name=None: connection.execute(
                text(f"DROP INDEX IF EXISTS {name}")
            ),
        )
        migration[action].__globals__["op"] = fake_op
        migration[action]()


def _create_schema():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE emails_templates (
                    id INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    codigo VARCHAR(50) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX ix_emails_templates_codigo "
                "ON emails_templates (codigo)"
            )
        )
    return engine


def _index_map(engine):
    return {
        index["name"]: index
        for index in inspect(engine).get_indexes("emails_templates")
    }


def _insert_template(engine, *, tenant_id: str, codigo: str):
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO emails_templates (tenant_id, codigo) "
                "VALUES (:tenant_id, :codigo)"
            ),
            {"tenant_id": tenant_id, "codigo": codigo},
        )


def _unique_constraints_for_model():
    constraints = []
    for constraint in EmailTemplate.__table__.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            constraints.append(
                (constraint.name, tuple(column.name for column in constraint.columns))
            )
    return constraints


def test_email_templates_migration_metadata():
    migration = _load_migration()

    assert migration["revision"] == "tm20260614a1"
    assert migration["down_revision"] == "tl20260614a1"
    assert migration["EMAIL_TEMPLATES_TABLE"] == "emails_templates"


def test_upgrade_troca_codigo_global_por_codigo_por_tenant():
    migration = _load_migration()
    engine = _create_schema()

    _run_migration(migration, engine, "upgrade")

    indexes = _index_map(engine)
    assert indexes["ix_emails_templates_codigo"]["unique"] == 0
    assert indexes["uq_emails_templates_tenant_codigo"]["unique"] == 1
    assert tuple(indexes["uq_emails_templates_tenant_codigo"]["column_names"]) == (
        "tenant_id",
        "codigo",
    )

    _insert_template(engine, tenant_id="tenant-a", codigo="ACERTO_PARCEIRO")
    _insert_template(engine, tenant_id="tenant-b", codigo="ACERTO_PARCEIRO")

    try:
        _insert_template(engine, tenant_id="tenant-a", codigo="ACERTO_PARCEIRO")
    except IntegrityError:
        pass
    else:
        raise AssertionError("codigo duplicado no mesmo tenant deveria falhar")


def test_downgrade_recria_codigo_global_unico():
    migration = _load_migration()
    engine = _create_schema()

    _run_migration(migration, engine, "upgrade")
    _run_migration(migration, engine, "downgrade")

    indexes = _index_map(engine)
    assert indexes["ix_emails_templates_codigo"]["unique"] == 1
    assert "uq_emails_templates_tenant_codigo" not in indexes


def test_modelo_email_template_declara_codigo_unico_por_tenant():
    assert EmailTemplate.__table__.c.codigo.unique is not True
    assert ("uq_emails_templates_tenant_codigo", ("tenant_id", "codigo")) in (
        _unique_constraints_for_model()
    )
