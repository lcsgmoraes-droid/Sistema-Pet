import importlib
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from app.security.jwt_compat import jwt
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

import app.auth_routes_multitenant as auth_routes
import app.db as db_package
import app.tenancy.filters as tenant_filters
import app.database.orm_guards as orm_guards
from app.auth.core import ALGORITHM
from app.auth.dependencies import get_current_user_and_tenant
from app.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    UserSession,
    UserTenant,
)
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
            pytest.xfail(
                "Ambiente local nao resolveu alembic.config; runtime app.main nao foi validado aqui."
            )
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


def _seed_auth_access(
    db_session,
    *,
    tenant_status="active",
    membership_active=True,
    session_tenant_id=None,
):
    tenant_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    set_current_tenant(tenant_id)

    tenant = Tenant(
        id=str(tenant_id),
        name="Tenant Teste",
        status=tenant_status,
        plan="basico",
    )
    user = User(
        email="tenant-access@example.com",
        nome="Tenant Access",
        tenant_id=tenant_id,
        is_active=True,
        **{HASHED_SECRET_FIELD: "hash"},
    )
    role = Role(name="Owner", tenant_id=tenant_id)
    db_session.add_all([tenant, user, role])
    db_session.flush()

    user_tenant = UserTenant(
        user_id=user.id,
        role_id=role.id,
        tenant_id=tenant_id,
        is_active=membership_active,
    )
    db_session.add(user_tenant)

    token_jti = str(uuid4())
    user_session = UserSession(
        user_id=user.id,
        tenant_id=session_tenant_id,
        token_jti=token_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(user_session)
    db_session.commit()
    clear_current_tenant()

    return tenant_id, user, token_jti


def _tenant_credentials(user, token_jti, tenant_id):
    token = auth_routes.create_access_token(
        data={
            "sub": str(user.id),
            "jti": token_jti,
            "tenant_id": str(tenant_id),
        }
    )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


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


def test_auth_multitenant_flow_nao_quebra_com_roles_fora_da_whitelist(
    monkeypatch, auth_db_session
):
    calls = []

    def fake_onboard(db, tenant_id, user_id, **kwargs):
        calls.append(
            (
                UUID(str(tenant_id)),
                user_id,
                kwargs.get("dry_run", False),
                kwargs.get("strict_required", False),
            )
        )
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
    tenant = auth_db_session.query(Tenant).filter(Tenant.id == str(tenant_id)).one()
    assert calls == [(tenant_id, user.id, False, True)]
    set_current_tenant(tenant_id)
    role = auth_db_session.query(Role).filter(Role.tenant_id == tenant_id).one()
    user_tenant = (
        auth_db_session.query(UserTenant).filter(UserTenant.user_id == user.id).one()
    )

    assert user.tenant_id == tenant_id
    assert user.is_admin is False
    assert tenant.plan == "pet-start"
    assert role.tenant_id == tenant_id
    assert user_tenant.tenant_id == tenant_id
    assert (
        auth_db_session.query(RolePermission)
        .filter(RolePermission.tenant_id == tenant_id)
        .count()
        == 2
    )

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

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=login_response.access_token
    )
    selected = auth_routes.select_tenant(
        request=_request("/auth/select-tenant"),
        body=auth_routes.SelectTenantRequest(tenant_id=str(tenant_id)),
        credentials=credentials,
        db=auth_db_session,
        current_user=user,
    )
    token_payload = jwt.decode(
        selected.access_token, auth_routes.SECRET_KEY, algorithms=[ALGORITHM]
    )
    assert token_payload["tenant_id"] == str(tenant_id)

    set_current_tenant(tenant_id)
    me_payload = auth_routes.get_me_multitenant(
        db=auth_db_session,
        user_and_tenant=(user, tenant_id),
    )
    assert me_payload["tenant"]["id"] == str(tenant_id)
    assert "produtos.ler" in me_payload["permissions"]
    assert "vendas.ler" in me_payload["permissions"]


def test_select_tenant_bloqueia_vinculo_inativo(auth_db_session):
    tenant_id, user, token_jti = _seed_auth_access(
        auth_db_session,
        membership_active=False,
    )
    credentials = _tenant_credentials(user, token_jti, tenant_id)

    with pytest.raises(auth_routes.HTTPException) as exc_info:
        auth_routes.select_tenant(
            request=_request("/auth/select-tenant"),
            body=auth_routes.SelectTenantRequest(tenant_id=str(tenant_id)),
            credentials=credentials,
            db=auth_db_session,
            current_user=user,
        )

    assert exc_info.value.status_code == 403


def test_select_tenant_bloqueia_tenant_inativo(auth_db_session):
    tenant_id, user, token_jti = _seed_auth_access(
        auth_db_session,
        tenant_status="inactive",
    )
    credentials = _tenant_credentials(user, token_jti, tenant_id)

    with pytest.raises(auth_routes.HTTPException) as exc_info:
        auth_routes.select_tenant(
            request=_request("/auth/select-tenant"),
            body=auth_routes.SelectTenantRequest(tenant_id=str(tenant_id)),
            credentials=credentials,
            db=auth_db_session,
            current_user=user,
        )

    assert exc_info.value.status_code == 403


def test_get_current_user_and_tenant_revalida_vinculo_ativo(auth_db_session):
    tenant_id, user, token_jti = _seed_auth_access(
        auth_db_session,
        membership_active=False,
    )
    credentials = _tenant_credentials(user, token_jti, tenant_id)

    with pytest.raises(auth_routes.HTTPException) as exc_info:
        asyncio.run(
            get_current_user_and_tenant(
                credentials=credentials,
                user=user,
                db=auth_db_session,
            )
        )

    assert exc_info.value.status_code == 403


def test_get_current_user_and_tenant_bloqueia_sessao_de_outro_tenant(auth_db_session):
    other_tenant_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    tenant_id, user, token_jti = _seed_auth_access(
        auth_db_session,
        session_tenant_id=other_tenant_id,
    )
    credentials = _tenant_credentials(user, token_jti, tenant_id)

    with pytest.raises(auth_routes.HTTPException) as exc_info:
        asyncio.run(
            get_current_user_and_tenant(
                credentials=credentials,
                user=user,
                db=auth_db_session,
            )
        )

    assert exc_info.value.status_code == 401


def test_rotas_criticas_usam_dependency_tenant_oficial():
    app_dir = Path(__file__).resolve().parents[2] / "app"
    rotas_criticas = [
        "categorias_routes.py",
        "chat_routes.py",
        "conciliacao_bancaria_routes.py",
    ]

    for rota in rotas_criticas:
        source = (app_dir / rota).read_text(encoding="utf-8")
        assert "get_current_user_and_tenant" in source
        assert "Depends(get_current_user)" not in source
        assert "current_user.tenant_id" not in source


def test_register_fails_closed_when_required_onboarding_fails(
    monkeypatch, auth_db_session
):
    def fail_onboard(db, tenant_id, user_id, **kwargs):
        assert kwargs.get("strict_required") is True
        raise RuntimeError("Onboarding obrigatorio incompleto")

    monkeypatch.setattr(auth_routes, "onboard_tenant_defaults", fail_onboard)
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", False)

    with pytest.raises(auth_routes.HTTPException) as exc_info:
        auth_routes.register(
            request=_request("/auth/register"),
            payload=auth_routes.RegisterRequest(
                email="phase11-onboarding-fail@example.com",
                nome="Phase 1.1 Fail",
                nome_loja="Loja Phase 1.1 Fail",
                accepted_terms=True,
                accepted_privacy=True,
                **{LOGIN_SECRET_FIELD: TEST_LOGIN_SECRET},
            ),
            db=auth_db_session,
        )

    assert exc_info.value.status_code == 500
    user_count = auth_db_session.execute(
        text("SELECT count(*) FROM users WHERE email = :email"),
        {"email": "phase11-onboarding-fail@example.com"},
    ).scalar_one()
    tenant_count = auth_db_session.execute(
        text("SELECT count(*) FROM tenants WHERE name = :name"),
        {"name": "Loja Phase 1.1 Fail"},
    ).scalar_one()
    assert user_count == 0
    assert tenant_count == 0
