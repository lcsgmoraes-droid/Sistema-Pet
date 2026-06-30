"""Fixtures compartilhadas dos testes da API de analytics."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.main import app


@pytest.fixture
def client():
    """Cliente de teste FastAPI com exceções convertidas em respostas HTTP"""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_user():
    """Mock de usuário autenticado"""
    user = Mock()
    user.id = 1
    user.nome = "Usuário Teste"
    user.is_admin = True
    user.tenant_id = "00000000-0000-0000-0000-000000000001"
    return user


@pytest.fixture
def override_auth(mock_user):
    """Override de autenticação para testes"""

    def override_get_current_user():
        return mock_user

    def override_get_current_user_and_tenant():
        return (mock_user, mock_user.tenant_id)

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_and_tenant] = (
        override_get_current_user_and_tenant
    )
    yield
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_current_user_and_tenant in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_and_tenant]


@pytest.fixture
def mock_db():
    """Mock de sessão do banco"""
    return Mock()


@pytest.fixture
def override_db(mock_db):
    """Override de sessão do banco para testes"""

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]
