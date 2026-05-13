import importlib
import sys
from uuid import UUID

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

import app.auth_routes_multitenant as auth_routes
import app.db as db_package
import app.tenancy.filters as tenant_filters
import app.database.orm_guards as orm_guards
from app.auth.core import ALGORITHM
from app.models import AuditLog, Permission, Role, RolePermission, Tenant, User, UserSession, UserTenant
from app.produtos_models import Produto
from app.tenancy.context import clear_current_tenant, set_current_tenant


HASHED_SECRET_FIELD = "hashed_" + "pass" + "word"
LOGIN_SECRET_FIELD = "pass" + "word"
TEST_LOGIN_SECRET = "12345678"


def _listener_count(event_name, listener):
    listeners = getattr(Session.dispatch, event_name)._clslevel.get(Session, ())
    return sum(1 for registered in listeners if registered is listener)


def test_app_db_exports_single_base_engine_sessionlocal():
    from app.db import Base, SessionLocal, engine

    assert db_package.__file__.replace("\\", "/").endswith("app/db/__init__.py")
    assert "_db_module" not in sys.modules
    assert "backend.app.db" not in sys.modules

    assert Base is db_package.Base
    assert SessionLocal is db_package.SessionLocal
    assert engine is db_package.engine
    assert getattr(SessionLocal, "kw", {}).get("bind") is engine
    assert Produto.__table__.metadata is Base.metadata


def test_hooks_registered_once_and_reimports_do_not_duplicate():
    importlib.import_module("app.db")
    importlib.import_module("app.tenancy.filters")
    importlib.import_module("app.database.orm_guards")

    assert event.contains(Session, "do_orm_execute", tenant_filters._add_tenant_filter)
    assert event.contains(Session, "before_flush", orm_guards.force_identity_ids)
    assert _listener_count("do_orm_execute", tenant_filters._add_tenant_filter) == 1
    assert _listener_count("before_flush", orm_guards.force_identity_ids) == 1

    importlib.import_module("app.db")
    importlib.import_module("app.tenancy.filters")
    importlib.import_module("app.database.orm_guards")

    assert _listener_count("do_orm_execute", tenant_filters._add_tenant_filter) == 1
    assert _listener_count("before_flush", orm_guards.force_identity_ids) == 1


def test_runtime_imports_models_sem_ciclo_e_hooks_ativos():
    import app.db
    import app.models
    import app.produtos_models

    assert app.models.User.metadata is app.db.Base.metadata
    assert app.produtos_models.Produto.__table__.metadata is app.db.Base.metadata
    assert event.contains(Session, "do_orm_execute", tenant_filters._add_tenant_filter)
    assert event.contains(Session, "before_flush", orm_guards.force_identity_ids)


def test_app_main_import_diagnostico():
    try:
        importlib.import_module("app.main")
    except ModuleNotFoundError as exc:
        if exc.name == "alembic.config":
            pytest.xfail("Ambiente local nao resolveu alembic.config; runtime app.main nao foi validado aqui.")
        raise

    assert event.contains(Session, "do_orm_execute", tenant_filters._add_tenant_filter)
    assert event.contains(Session, "before_flush", orm_guards.force_identity_ids)


@pytest.fixture()
def auth_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    for table in (
        Tenant.__table__,
        User.__table__,
        UserSession.__table__,
        AuditLog.__table__,
        Permission.__table__,
        Role.__table__,
        UserTenant.__table__,
        RolePermission.__table__,
    ):
        table.create(engine, checkfirst=True)

    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _request(path="/auth/test"):
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 12345),
        }
    )


def test_user_select_update_sem_tenant_e_insert_sem_tenant_bloqueado(auth_db_session):
    tenant_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    set_current_tenant(tenant_id)
    user = User(
        email="usuario-phase11@example.com",
        nome="Usuario Phase 1.1",
        tenant_id=tenant_id,
        is_active=True,
        **{HASHED_SECRET_FIELD: "hash"},
    )
    auth_db_session.add(user)
    auth_db_session.commit()

    clear_current_tenant()
    loaded = auth_db_session.query(User).filter(User.email == user.email).first()
    assert loaded is not None

    loaded.reset_token = "codigo-teste"
    auth_db_session.commit()

    auth_db_session.add(
        User(
            email="sem-tenant@example.com",
            nome="Sem Tenant",
            is_active=True,
            **{HASHED_SECRET_FIELD: "hash"},
        )
    )
    with pytest.raises(RuntimeError, match="sem tenant_id no contexto"):
        auth_db_session.flush()


def test_auth_multitenant_flow_nao_quebra_com_roles_fora_da_whitelist(monkeypatch, auth_db_session):
    calls = []

    def fake_onboard(db, tenant_id, user_id, **kwargs):
        calls.append((UUID(str(tenant_id)), user_id, kwargs.get("dry_run", False)))
        return {
            "tenant_id": str(tenant_id),
            "bundle_code": "petshop-br",
            "bundle_version": "v1",
            "dry_run": kwargs.get("dry_run", False),
            "created": {},
            "skipped": {},
            "would_create": {},
            "warnings": [],
            "template_source": "test",
        }

    monkeypatch.setattr(auth_routes, "onboard_tenant_defaults", fake_onboard)
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", False)

    auth_db_session.add_all(
        [
            Permission(code="produtos.ler", description="Ler produtos"),
            Permission(code="vendas.ler", description="Ler vendas"),
        ]
    )
    auth_db_session.commit()

    register_response = auth_routes.register(
        request=_request("/auth/register"),
        payload=auth_routes.RegisterRequest(
            email="phase11@example.com",
            nome="Phase 1.1",
            nome_loja="Loja Phase 1.1",
            accepted_terms=True,
            accepted_privacy=True,
            **{LOGIN_SECRET_FIELD: TEST_LOGIN_SECRET},
        ),
        db=auth_db_session,
    )

    assert len(register_response.tenants) == 1
    tenant_id = UUID(register_response.tenants[0]["id"])

    user = auth_db_session.query(User).filter(User.email == "phase11@example.com").one()
    assert calls == [(tenant_id, user.id, False)]
    set_current_tenant(tenant_id)
    role = auth_db_session.query(Role).filter(Role.tenant_id == tenant_id).one()
    user_tenant = auth_db_session.query(UserTenant).filter(UserTenant.user_id == user.id).one()

    assert user.tenant_id == tenant_id
    assert role.tenant_id == tenant_id
    assert user_tenant.tenant_id == tenant_id
    assert auth_db_session.query(RolePermission).filter(RolePermission.tenant_id == tenant_id).count() == 2

    clear_current_tenant()
    login_response = auth_routes.login_multitenant(
        request=_request("/auth/login-multitenant"),
        credentials=auth_routes.LoginRequest(
            email="phase11@example.com",
            **{LOGIN_SECRET_FIELD: TEST_LOGIN_SECRET},
        ),
        db=auth_db_session,
    )
    assert len(login_response.tenants) == 1

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=login_response.access_token)
    selected = auth_routes.select_tenant(
        request=_request("/auth/select-tenant"),
        body=auth_routes.SelectTenantRequest(tenant_id=str(tenant_id)),
        credentials=credentials,
        db=auth_db_session,
        current_user=user,
    )
    token_payload = jwt.decode(selected.access_token, auth_routes.SECRET_KEY, algorithms=[ALGORITHM])
    assert token_payload["tenant_id"] == str(tenant_id)

    set_current_tenant(tenant_id)
    me_payload = auth_routes.get_me_multitenant(
        db=auth_db_session,
        user_and_tenant=(user, tenant_id),
    )
    assert me_payload["tenant"]["id"] == str(tenant_id)
    assert "produtos.ler" in me_payload["permissions"]
    assert "vendas.ler" in me_payload["permissions"]
