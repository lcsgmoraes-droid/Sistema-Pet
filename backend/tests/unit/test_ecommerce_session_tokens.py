from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.models import Tenant, User, UserTenant
from app.routes import ecommerce_auth_common
from app.routes.ecommerce_auth_common import (
    ECOMMERCE_ACCESS_TOKEN_TYPE,
    ECOMMERCE_REFRESH_TOKEN_TYPE,
    MOBILE_SESSION_EXPIRE_DAYS,
    _create_ecommerce_token_pair,
    _issue_ecommerce_profile_tokens,
    _refresh_ecommerce_session,
)
from app.security.jwt_compat import jwt


def test_ecommerce_token_pair_separa_acesso_e_renovacao():
    tenant_id = str(uuid4())
    token_jti = str(uuid4())
    user = SimpleNamespace(id=42, email="cliente@corepet.com.br")
    session_expiry = datetime.now(timezone.utc) + timedelta(days=7)

    access_token, refresh_token = _create_ecommerce_token_pair(
        user,
        tenant_id,
        token_jti,
        session_expiry,
    )

    access_payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    refresh_payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

    assert access_payload["typ"] == "access"
    assert access_payload["token_type"] == ECOMMERCE_ACCESS_TOKEN_TYPE
    assert refresh_payload["typ"] == "refresh"
    assert refresh_payload["token_type"] == ECOMMERCE_REFRESH_TOKEN_TYPE
    assert access_payload["jti"] == refresh_payload["jti"] == token_jti
    assert access_payload["tenant_id"] == refresh_payload["tenant_id"] == tenant_id
    assert access_payload["exp"] < refresh_payload["exp"]


def test_access_token_nao_pode_ser_usado_para_renovar_sessao():
    tenant_id = str(uuid4())
    user = SimpleNamespace(id=42, email="cliente@corepet.com.br")
    access_token, _ = _create_ecommerce_token_pair(
        user,
        tenant_id,
        str(uuid4()),
        datetime.now(timezone.utc) + timedelta(days=7),
    )

    with pytest.raises(HTTPException) as exc_info:
        _refresh_ecommerce_session(access_token, db=None)

    assert exc_info.value.status_code == 401


def test_refresh_valido_renova_acesso_da_mesma_sessao_e_loja(monkeypatch):
    tenant_id = uuid4()
    token_jti = str(uuid4())
    session_expiry = datetime.now(timezone.utc) + timedelta(days=7)
    user = SimpleNamespace(id=42, email="cliente@corepet.com.br", is_active=True)
    user_tenant = SimpleNamespace(user_id=42, tenant_id=tenant_id, is_active=True)
    tenant = SimpleNamespace(id=tenant_id, status="active")
    db_session = SimpleNamespace(
        user_id=42,
        tenant_id=tenant_id,
        token_jti=token_jti,
        expires_at=session_expiry,
    )

    class QueryStub:
        def __init__(self, result):
            self.result = result

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self.result

    class DbStub:
        def query(self, model):
            return QueryStub(
                {
                    User: user,
                    UserTenant: user_tenant,
                    Tenant: tenant,
                }[model]
            )

    _, refresh_token = _create_ecommerce_token_pair(
        user,
        str(tenant_id),
        token_jti,
        session_expiry,
    )

    monkeypatch.setattr(
        ecommerce_auth_common, "set_current_tenant", lambda _tenant: None
    )
    monkeypatch.setattr(
        ecommerce_auth_common, "sync_rls_auth_user", lambda _db, _user_id: None
    )
    monkeypatch.setattr(
        ecommerce_auth_common, "validate_session", lambda _db, _jti: True
    )
    monkeypatch.setattr(
        ecommerce_auth_common,
        "get_session_by_jti",
        lambda _db, _jti: db_session,
    )

    response = _refresh_ecommerce_session(refresh_token, DbStub())
    renewed_access = jwt.decode(
        response["access_token"], JWT_SECRET_KEY, algorithms=[ALGORITHM]
    )

    assert renewed_access["typ"] == "access"
    assert renewed_access["token_type"] == ECOMMERCE_ACCESS_TOKEN_TYPE
    assert renewed_access["jti"] == token_jti
    assert renewed_access["tenant_id"] == str(tenant_id)
    assert response["refresh_token"]


def test_selecao_de_perfil_preserva_sessao_e_refresh_token(monkeypatch):
    tenant_id = uuid4()
    token_jti = str(uuid4())
    user = SimpleNamespace(
        id=42,
        email="cliente@corepet.com.br",
        tenant_id=tenant_id,
        _auth_session_jti=token_jti,
    )
    db_session = SimpleNamespace(
        user_id=42,
        tenant_id=tenant_id,
        token_jti=token_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        last_activity_at=datetime.now(timezone.utc),
    )

    class DbStub:
        def __init__(self):
            self.commits = 0

        def commit(self):
            self.commits += 1

    db = DbStub()
    request = SimpleNamespace(headers={"X-Client-Channel": "app"})
    monkeypatch.setattr(
        ecommerce_auth_common, "validate_session", lambda _db, _jti: True
    )
    monkeypatch.setattr(
        ecommerce_auth_common,
        "get_session_by_jti",
        lambda _db, _jti: db_session,
    )

    response = _issue_ecommerce_profile_tokens(
        db, user, str(tenant_id), request, "cliente"
    )
    access_payload = jwt.decode(
        response["access_token"], JWT_SECRET_KEY, algorithms=[ALGORITHM]
    )
    refresh_payload = jwt.decode(
        response["refresh_token"], JWT_SECRET_KEY, algorithms=[ALGORITHM]
    )

    assert access_payload["jti"] == refresh_payload["jti"] == token_jti
    assert access_payload["active_profile"] == "cliente"
    assert refresh_payload["active_profile"] == "cliente"
    assert db_session.expires_at > datetime.now(timezone.utc) + timedelta(
        days=MOBILE_SESSION_EXPIRE_DAYS - 1
    )
    assert db.commits == 1


def test_refresh_mobile_renova_prazo_e_preserva_perfil(monkeypatch):
    tenant_id = uuid4()
    token_jti = str(uuid4())
    session_expiry = datetime.now(timezone.utc) + timedelta(days=7)
    user = SimpleNamespace(id=42, email="cliente@corepet.com.br", is_active=True)
    user_tenant = SimpleNamespace(user_id=42, tenant_id=tenant_id, is_active=True)
    tenant = SimpleNamespace(id=tenant_id, status="active")
    db_session = SimpleNamespace(
        user_id=42,
        tenant_id=tenant_id,
        token_jti=token_jti,
        expires_at=session_expiry,
        last_activity_at=datetime.now(timezone.utc),
    )

    class QueryStub:
        def __init__(self, result):
            self.result = result

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self.result

    class DbStub:
        def __init__(self):
            self.commits = 0

        def query(self, model):
            return QueryStub(
                {
                    User: user,
                    UserTenant: user_tenant,
                    Tenant: tenant,
                }[model]
            )

        def commit(self):
            self.commits += 1

    db = DbStub()
    request = SimpleNamespace(headers={"X-Client-Channel": "app"})
    _, refresh_token = _create_ecommerce_token_pair(
        user,
        str(tenant_id),
        token_jti,
        session_expiry,
        active_profile="cliente",
    )
    monkeypatch.setattr(
        ecommerce_auth_common, "set_current_tenant", lambda _tenant: None
    )
    monkeypatch.setattr(
        ecommerce_auth_common, "sync_rls_auth_user", lambda _db, _user_id: None
    )
    monkeypatch.setattr(
        ecommerce_auth_common, "validate_session", lambda _db, _jti: True
    )
    monkeypatch.setattr(
        ecommerce_auth_common,
        "get_session_by_jti",
        lambda _db, _jti: db_session,
    )

    response = _refresh_ecommerce_session(refresh_token, db, request)
    next_refresh = jwt.decode(
        response["refresh_token"], JWT_SECRET_KEY, algorithms=[ALGORITHM]
    )

    assert next_refresh["active_profile"] == "cliente"
    assert db_session.expires_at > datetime.now(timezone.utc) + timedelta(
        days=MOBILE_SESSION_EXPIRE_DAYS - 1
    )
    assert db.commits == 1
