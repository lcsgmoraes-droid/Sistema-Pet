"""
Configuração mínima para testes do tenant_safe_sql
"""
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adicionar backend ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configurar DATABASE_URL para testes
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
)

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture de sessão de banco de dados com rollback automático"""
    session = TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
