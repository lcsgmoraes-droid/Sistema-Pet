"""RLS real em PostgreSQL descartavel; nunca usa DATABASE_URL da aplicacao."""

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


@pytest.fixture
def pg_pilot():
    url = os.environ.get("INTNFE_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Defina INTNFE_TEST_POSTGRES_URL para PostgreSQL local descartavel")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database == "intnfe_test", (
        "Este teste exige banco descartavel dedicado"
    )
    engine = create_engine(url)
    schema = f"intnfe_test_{uuid4().hex}"
    role = f"intnfe_role_{uuid4().hex}"
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzn20260909a1_intnfe_activation.py"
    )
    spec = importlib.util.spec_from_file_location("intnfe_pg_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    tenant_a, tenant_b = str(uuid4()), str(uuid4())
    with engine.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
        connection.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        connection.exec_driver_sql(f"CREATE ROLE {role} NOSUPERUSER NOBYPASSRLS")
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
        connection.exec_driver_sql(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema} TO {role}"
        )
        connection.exec_driver_sql(
            f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA {schema} TO {role}"
        )
        for tenant, cnpj in (
            (tenant_a, "11222333000181"),
            (tenant_b, "11444777000161"),
        ):
            connection.execute(
                text(
                    "INSERT INTO intnfe_connections (tenant_id,cnpj,razao_social,nome_fantasia,integrador_id) VALUES (:tenant,:cnpj,'Loja Ficticia','Loja Ficticia','integrador-ficticio')"
                ),
                {"tenant": tenant, "cnpj": cnpj},
            )

    def scoped(connection, tenant):
        connection.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
        connection.exec_driver_sql(f"SET LOCAL ROLE {role}")
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": tenant},
        )

    yield engine, scoped, tenant_a, tenant_b, schema
    # Somente o schema e papel exclusivos criados por esta fixture.
    with engine.begin() as connection:
        connection.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert not inspect(connection).has_table("intnfe_connections", schema=schema)
        connection.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
        connection.exec_driver_sql(f"DROP ROLE {role}")
    engine.dispose()


def test_postgres_rls_blocks_cross_tenant_reads_updates_and_deletes(pg_pilot):
    engine, scoped, tenant_a, tenant_b, _schema = pg_pilot
    for tenant in (tenant_a, tenant_b, ""):
        with engine.begin() as connection:
            scoped(connection, tenant)
            rows = (
                connection.execute(text("SELECT tenant_id FROM intnfe_connections"))
                .scalars()
                .all()
            )
            assert [str(row) for row in rows] == ([tenant] if tenant else [])
            foreign = tenant_b if tenant == tenant_a else tenant_a
            assert (
                connection.execute(
                    text(
                        "UPDATE intnfe_connections SET status='indevido' WHERE tenant_id=:tenant"
                    ),
                    {"tenant": foreign},
                ).rowcount
                == 0
            )
            assert (
                connection.execute(
                    text("DELETE FROM intnfe_connections WHERE tenant_id=:tenant"),
                    {"tenant": foreign},
                ).rowcount
                == 0
            )


def test_postgres_rls_rejects_cross_tenant_writes_and_cnpj_reuse(pg_pilot):
    engine, scoped, tenant_a, tenant_b, _schema = pg_pilot
    for tenant, expected in ((tenant_b, "42501"), (tenant_a, "23505")):
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                scoped(connection, tenant_a)
                connection.execute(
                    text(
                        "INSERT INTO intnfe_connections (tenant_id,cnpj,razao_social,nome_fantasia,integrador_id) VALUES (:tenant,'11222333000181','Ficticia','Ficticia','ficticio')"
                    ),
                    {"tenant": tenant},
                )
        assert caught.value.orig.pgcode == expected


def test_postgres_concurrent_reservations_have_a_single_winner(pg_pilot, monkeypatch):
    from app.intnfe.repository import ActivationError, reserve
    from app.models import Tenant
    from app.tenancy.context import tenant_context

    engine, _scoped, tenant_a, _tenant_b, schema = pg_pilot
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "chave-ficticia-postgres")
    with engine.begin() as connection:
        connection.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
        Tenant.__table__.create(connection)
        connection.execute(
            Tenant.__table__.insert().values(
                id=tenant_a,
                name="Loja Ficticia",
                name_normalized=tenant_a,
                razao_social="Loja Ficticia",
                cnpj="11222333000181",
            )
        )
    barrier = Barrier(2)

    def attempt():
        with engine.connect() as connection:
            connection.exec_driver_sql(f"SET search_path TO {schema}")
            connection.commit()
            with Session(bind=connection) as session, tenant_context(tenant_a):
                barrier.wait(timeout=10)
                try:
                    reserve(session, tenant_a, "integrador-ficticio")
                    return "reservado"
                except ActivationError as exc:
                    assert "andamento" in str(exc)
                    return "bloqueado"

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _index: attempt(), range(2)))
    assert sorted(results) == ["bloqueado", "reservado"]
