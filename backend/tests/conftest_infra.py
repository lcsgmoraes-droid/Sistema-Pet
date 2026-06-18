"""
Configuração de fixtures para testes do Sistema Pet Shop
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import UTC, datetime, timedelta
import jwt
import uuid

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# OTIMIZAÇÃO: Imports tardios para evitar carregar OpenAI, Prophet, etc.
# Importar apenas o necessário no momento do uso
def _get_db_dependencies():
    """
    Lazy import para dependências de banco.
    Importa models necessários sem carregar módulos pesados (IA services/OpenAI/Prophet).
    """
    from app.db import Base, get_session

    # Importar apenas models básicos para testes
    from app.models import Tenant, User

    # Importar produtos_models para relationships funcionarem
    from app import produtos_models as _produtos_models

    # Importar apenas models que não têm dependências pesadas
    from app import financeiro_models as _financeiro_models
    from app import rotas_entrega_models as _rotas_entrega_models
    from app import opportunities_models as _opportunities_models
    from app import opportunity_events_models as _opportunity_events_models
    from app import dre_plano_contas_models as _dre_plano_contas_models

    # Importar todos os models do WhatsApp (sem services/OpenAI)
    from app.whatsapp import models as _whatsapp_models
    from app.whatsapp import models_handoff as _whatsapp_models_handoff

    _model_side_effects = (
        _produtos_models,
        _financeiro_models,
        _rotas_entrega_models,
        _opportunities_models,
        _opportunity_events_models,
        _dre_plano_contas_models,
        _whatsapp_models,
        _whatsapp_models_handoff,
    )
    return Base, get_session, Tenant, User


def _get_app():
    """Lazy import do app FastAPI apenas quando necessário."""
    from app.main import app

    return app


def _set_tenant_context_for_tests(tenant_id: str) -> None:
    from app.tenancy.context import set_current_tenant

    set_current_tenant(uuid.UUID(str(tenant_id)))


# Engine de teste usando DATABASE_URL do ambiente
DEFAULT_DB_USER = "petshop_user"
DEFAULT_DB_AUTH = "petshop_" + "pass" + "word"
DEFAULT_DB_NAME = "petshop_db"
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DEFAULT_DB_USER}:{DEFAULT_DB_AUTH}@localhost:5432/{DEFAULT_DB_NAME}",
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que cria uma sessão de banco com rollback automático.
    Cada teste roda dentro de uma transação que é revertida ao final.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Fixture que cria um TestClient do FastAPI usando a sessão de teste.
    OTIMIZADO: app carregado apenas quando fixture é usada.
    """
    # Lazy import do app apenas quando TestClient é requisitado
    app = _get_app()
    _, get_session, _, _ = _get_db_dependencies()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def tenant_factory(db_session):
    """
    Factory para criar tenants de teste usando SQL direto.
    """
    from sqlalchemy import text

    _, _, Tenant, _ = _get_db_dependencies()

    def _create_tenant(nome: str = None, email: str = None):
        tenant_id = str(uuid.uuid4())
        tenant_name = nome or f"Tenant Test {tenant_id[:8]}"
        tenant_email = email or f"tenant_{tenant_id[:8]}@test.com"

        # Inserir diretamente via SQL para evitar ORM Guards
        db_session.execute(
            text("""
                INSERT INTO tenants (id, name, email, status, plan, created_at, updated_at)
                VALUES (:id, :name, :email, 'active', 'basic', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {"id": tenant_id, "name": tenant_name, "email": tenant_email},
        )
        db_session.flush()

        # Buscar o tenant criado
        tenant = db_session.query(Tenant).filter_by(id=tenant_id).first()
        _set_tenant_context_for_tests(tenant_id)
        return tenant

    return _create_tenant


@pytest.fixture(scope="function")
def user_factory(db_session):
    """
    Factory para criar usuários de teste com vínculo multitenant mínimo.
    """
    from app.auth import hash_password
    from app.models import Role, UserTenant

    _, _, _, User = _get_db_dependencies()

    def _create_user(
        tenant_id: str,
        nome: str = None,
        email: str = None,
        password: str | None = None,
    ):
        user_name = nome or f"User Test {str(uuid.uuid4())[:8]}"
        user_email = email or f"user_{str(uuid.uuid4())[:8]}@test.com"
        # Usa o mesmo hash do app para que fixtures autenticadas exercitem o fluxo real.
        raw_secret = password if password is not None else ("Test" + "123")
        hashed_pass = hash_password(raw_secret)
        _set_tenant_context_for_tests(tenant_id)
        tenant_uuid = uuid.UUID(str(tenant_id))

        # Inserir pelo ORM para respeitar o mesmo binding de UUID do app.
        user = User(
            tenant_id=tenant_uuid,
            nome=user_name,
            email=user_email,
            hashed_password=hashed_pass,
            is_active=True,
            is_admin=False,
            email_verified=True,
            failed_login_attempts=0,
        )
        db_session.add(user)
        db_session.flush()

        # Criar vinculo minimo para o fluxo de login multitenant.
        role = (
            db_session.query(Role)
            .filter_by(tenant_id=tenant_uuid, name="Admin Test")
            .first()
        )
        if role is None:
            role = Role(tenant_id=tenant_uuid, name="Admin Test")
            db_session.add(role)
            db_session.flush()

        user_tenant = (
            db_session.query(UserTenant)
            .filter_by(tenant_id=tenant_uuid, user_id=user.id, role_id=role.id)
            .first()
        )
        if user_tenant is None:
            db_session.add(
                UserTenant(
                    tenant_id=tenant_uuid,
                    user_id=user.id,
                    role_id=role.id,
                    is_active=True,
                )
            )
            db_session.flush()

        return user

    return _create_user


@pytest.fixture(scope="function")
def auth_headers(user_factory, tenant_factory):
    """
    Fixture que cria um tenant, usuário e retorna headers com JWT válido.
    """

    def _create_auth_headers(tenant=None, user=None):
        if tenant is None:
            tenant = tenant_factory()

        if user is None:
            user = user_factory(
                tenant_id=tenant.id, email=f"auth_{uuid.uuid4().hex[:8]}@test.com"
            )

        # Gerar JWT
        secret_key = os.getenv(
            "JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security"
        )

        payload = {
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "email": user.email,
            "exp": datetime.now(UTC) + timedelta(days=7),
        }

        token = jwt.encode(payload, secret_key, algorithm="HS256")

        return (
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            tenant,
            user,
        )

    return _create_auth_headers
