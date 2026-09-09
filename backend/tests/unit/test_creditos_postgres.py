"""Smoke opt-in em PostgreSQL DESCARTÁVEL; nunca usa DATABASE_URL da aplicação.

COREPET_CREDITOS_TEST_POSTGRES_URL deve apontar a localhost e banco cujo nome
comece com corepet_creditos_test_. O papel deve ser proprietário não-superuser.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.services import creditos_service as service
from app.services.creditos_catalog import CreditosError
from app.tenancy.context import clear_current_tenant
from tests.unit.test_creditos_migration import load_migration


TEST_URL = os.getenv("COREPET_CREDITOS_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(
    not TEST_URL, reason="PostgreSQL descartável não solicitado"
)
TENANT = "321f02b4-fa86-47c8-a394-a04b7071ca64"
OTHER = "e9db558f-2fc7-4eae-a780-75207ec2f2db"
PAYLOAD = {"nome": "Produto fictício"}
CODE = "produto.descricao_fiscal"


@pytest.fixture
def pg_case(monkeypatch):
    url = make_url(TEST_URL)
    assert url.host in {"127.0.0.1", "localhost"}
    assert url.database.startswith("corepet_creditos_test_")
    engine = create_engine(url)
    with engine.connect() as connection:
        database, superuser, bypass_rls = connection.execute(
            text(
                "SELECT current_database(), rolsuper, rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        assert database == url.database
        assert superuser is False, "RLS deve ser testado com papel não-superuser"
        assert bypass_rls is False, "RLS deve ser testado com papel sem BYPASSRLS"
    metadata = MetaData()
    tenants = Table("tenants", metadata, Column("id", String(36), primary_key=True))
    users = Table("users", metadata, Column("id", Integer, primary_key=True))
    migration = load_migration()
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(tenants.insert(), [{"id": TENANT}, {"id": OTHER}])
        connection.execute(users.insert(), [{"id": 1}, {"id": 2}])
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        migration.upgrade()
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": TENANT},
        )
        connection.execute(
            text(
                "INSERT INTO creditos_wallets (tenant_id, available_credits, reserved_credits) VALUES (:tenant,125,0)"
            ),
            {"tenant": TENANT},
        )
    monkeypatch.setenv("COREPET_CREDITOS_MODE", "enforced")
    monkeypatch.setenv("COREPET_CREDITOS_TENANT_ALLOWLIST", f"{TENANT},{OTHER}")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    clear_current_tenant()
    try:
        yield factory, engine
    finally:
        clear_current_tenant()
        with engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.downgrade()
            metadata.drop_all(connection)
        engine.dispose()


def _quote(db):
    return service.quote(
        db, UUID(TENANT), 1, CODE, PAYLOAD, idempotency_key=str(uuid4())
    )


@pytest.mark.parametrize("same_operation", [True, False])
def test_postgres_concurrency_reserves_only_once(pg_case, same_operation):
    factory, _ = pg_case
    with factory() as db:
        first = _quote(db)
        second = first if same_operation else _quote(db)
    barrier = Barrier(2)

    def run(operation):
        clear_current_tenant()
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                return service.start_operation(
                    db, TENANT, 1, operation["operation_id"], CODE, PAYLOAD
                )["should_execute"]
            except CreditosError as exc:
                assert exc.code == "insufficient_credits"
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, (first, second)))
    assert results.count(True) == 1
    with factory() as db:
        wallet = service.get_wallet(db, TENANT)
        assert (wallet["available_credits"], wallet["reserved_credits"]) == (0, 125)
        assert len(service.get_ledger(db, TENANT)["items"]) == 1


def test_postgres_rls_and_ledger_direct_sql_immutable(pg_case):
    factory, engine = pg_case
    with factory() as db:
        operation = _quote(db)
        service.start_operation(db, TENANT, 1, operation["operation_id"], CODE, PAYLOAD)
        service.complete_operation(
            db, TENANT, 1, operation["operation_id"], result_payload={"ok": True}
        )
    with engine.begin() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM creditos_wallets")
            ).scalar_one()
            == 0
        )
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": OTHER}
        )
        for table in ("creditos_wallets", "creditos_operations", "creditos_ledger"):
            assert (
                connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                == 0
            )
        connection.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": TENANT},
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM creditos_ledger")
            ).scalar_one()
            == 2
        )
    for sql in (
        "UPDATE creditos_ledger SET title='bad'",
        "DELETE FROM creditos_ledger",
        "TRUNCATE creditos_ledger",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            with engine.begin() as connection:
                connection.execute(
                    text("SELECT set_config('app.tenant_id', :tenant, true)"),
                    {"tenant": TENANT},
                )
                connection.execute(text(sql))
    with pytest.raises(DBAPIError, match="row-level security"):
        with engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant, true)"),
                {"tenant": OTHER},
            )
            connection.execute(
                text("INSERT INTO creditos_wallets(tenant_id) VALUES (:tenant)"),
                {"tenant": str(uuid4())},
            )
    with factory() as db:
        assert service.get_wallet(db, OTHER)["available_credits"] == 0
        assert service.get_ledger(db, OTHER)["items"] == []


def test_postgres_fk_tenant_and_result_pending_resolution(pg_case):
    factory, engine = pg_case
    unknown = str(uuid4())
    with pytest.raises(DBAPIError, match="foreign key"):
        with engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant, true)"),
                {"tenant": unknown},
            )
            connection.execute(
                text("INSERT INTO creditos_wallets(tenant_id) VALUES (:tenant)"),
                {"tenant": unknown},
            )
    with factory() as db:
        operation = _quote(db)
        op_id = operation["operation_id"]
        service.start_operation(db, TENANT, 1, op_id, CODE, PAYLOAD)
        service.fail_operation(db, TENANT, 1, op_id, failure_code="timeout")
    with factory() as db:
        pending = service.start_operation(db, TENANT, 1, op_id, CODE, PAYLOAD)
        assert pending["status"] == "uncertain" and pending["should_execute"] is False
        assert service.get_wallet(db, TENANT)["reserved_credits"] == 125
        service.fail_operation(
            db,
            TENANT,
            1,
            op_id,
            failure_code="provider_rejected",
            definite_failure=True,
        )
        wallet = service.get_wallet(db, TENANT)
        assert (wallet["available_credits"], wallet["reserved_credits"]) == (125, 0)
