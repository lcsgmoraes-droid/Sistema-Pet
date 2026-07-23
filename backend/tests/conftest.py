"""
Minimal conftest for unit and legacy integration-style tests.

The legacy root tests import ORM models during collection, so test defaults must
exist before those imports happen.
"""

import sys
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the backend package root (backend/) is in path.
backend_dir = os.path.abspath(os.path.dirname(__file__) + os.sep + "..")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


# Database URL for tests
DEFAULT_TEST_DATABASE_URL = "sqlite://"
os.environ.setdefault("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security"
)

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@compiles(PostgreSQLUUID, "sqlite")
def _compile_postgresql_uuid_for_sqlite(_type, _compiler, **_kw):
    """Allow legacy ORM tests to run without a local PostgreSQL service."""
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, _compiler, **_kw):
    """Allow product metadata JSONB columns in lightweight SQLite tests."""
    return "JSON"


# Re-export legacy factory fixtures without replacing the canonical db_session.
from tests.conftest_infra import (  # noqa: E402
    auth_headers as _auth_headers,
    tenant_factory as _tenant_factory,
    user_factory as _user_factory,
)

auth_headers = _auth_headers
tenant_factory = _tenant_factory
user_factory = _user_factory


def _is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _create_engine_kwargs(database_url: str) -> dict:
    if _is_sqlite_url(database_url):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {"pool_pre_ping": True}


def _create_sqlite_schema(engine) -> None:
    from app.db import Base
    from app import (  # noqa: F401
        caixa_models,
        dre_plano_contas_models,
        financeiro_models,
        models,
        produtos_models,
        vendas_models,
    )

    Base.metadata.create_all(engine)
    from app.db.migration_check import _get_alembic_head

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(64) NOT NULL)"
            )
        )
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": _get_alembic_head(engine)},
        )


@pytest.fixture(autouse=True)
def clear_rate_limit_store():
    """Limpa stores globais antes e depois de cada teste."""
    from app.middlewares.rate_limit import rate_limit_store
    from app.tenancy.context import clear_current_tenant

    clear_current_tenant()
    rate_limit_store.clear()
    yield
    clear_current_tenant()
    rate_limit_store.clear()


@pytest.fixture
def dummy_fixture():
    """Dummy fixture to ensure conftest is loaded."""
    return True


@pytest.fixture
def client(db_session, db_engine, monkeypatch):
    """FastAPI test client wired to the isolated test session."""
    from fastapi.testclient import TestClient

    import app.db as app_db
    import app.db.core as app_db_core
    from app.db import get_session

    monkeypatch.setattr(app_db, "engine", db_engine)
    monkeypatch.setattr(app_db_core, "engine", db_engine)

    from app.main import app

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def tenant_context():
    """Set the current tenant context for ORM tenant-safe tests."""
    from uuid import UUID

    from app.tenancy.context import clear_current_tenant, set_current_tenant

    def _set_tenant(tenant_id):
        set_current_tenant(UUID(str(tenant_id)))

    yield _set_tenant
    clear_current_tenant()


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for tests."""
    engine = create_engine(
        TEST_DATABASE_URL, **_create_engine_kwargs(TEST_DATABASE_URL)
    )
    if _is_sqlite_url(TEST_DATABASE_URL):
        _create_sqlite_schema(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a database session isolated by an outer transaction."""
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def db(db_session):
    """Legacy alias for tests written before the db_session fixture name."""
    from uuid import UUID

    from app.tenancy.context import clear_current_tenant, set_current_tenant

    set_current_tenant(UUID("00000000-0000-0000-0000-000000000001"))
    try:
        yield db_session
    finally:
        clear_current_tenant()


@pytest.fixture
def normal_user_token(auth_headers):
    """Legacy token fixture for tests that assert non-admin access is forbidden."""
    headers, _tenant, _user = auth_headers()
    return headers["Authorization"].removeprefix("Bearer ")


@pytest.fixture
def admin_user_token(auth_headers, db_session):
    """Legacy token fixture for read-only admin API tests."""
    headers, _tenant, user = auth_headers()
    user.is_admin = True
    db_session.flush()
    return headers["Authorization"].removeprefix("Bearer ")
