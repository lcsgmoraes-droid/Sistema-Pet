"""
Minimal conftest for unit tests.

For integration tests, import from conftest_infra.py manually.
"""
import pytest
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend is in path
backend_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


# Database URL for tests
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
)


@pytest.fixture(autouse=True)
def clear_rate_limit_store():
    """Limpa o rate limit store antes de cada teste."""
    from app.middlewares.rate_limit import rate_limit_store
    rate_limit_store.clear()
    yield
    rate_limit_store.clear()


@pytest.fixture
def dummy_fixture():
    """Dummy fixture to ensure conftest is loaded."""
    return True


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for tests."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a database session with automatic rollback."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()

