from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app import produtos_models  # noqa: F401 - registra relacionamentos do ORM
from app.auth import verify_password
from app.auth.auth_multitenant_account_routes import login_multitenant
from app.auth.auth_multitenant_schemas import LoginRequest
from app.models import Role, Tenant, User, UserTenant
from app.routes.ecommerce_auth_public import login_cliente
from app.routes.ecommerce_auth_schemas import EcommerceLoginRequest
from app.services.user_account_service import (
    UserAccountError,
    create_tenant_user_account,
    normalize_username,
)
from app.tenancy.context import set_tenant_context
from app.usuarios_routes import UserCredentialsUpdate, atualizar_credenciais_usuario


REPO_ROOT = Path(__file__).resolve().parents[2]


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Tenant.__table__.create(engine)
    Role.__table__.create(engine)
    User.__table__.create(engine)
    UserTenant.__table__.create(engine)
    return Session(engine)


def _tenant(db: Session, *, name: str = "Loja Teste") -> Tenant:
    tenant = Tenant(
        id=str(uuid4()),
        name=name,
        name_normalized=name.lower(),
        ecommerce_slug=name.lower().replace(" ", "-"),
        status="active",
        plan="pet-start",
    )
    db.add(tenant)
    db.commit()
    set_tenant_context(UUID(str(tenant.id)))
    return tenant


def _account(db: Session, tenant: Tenant, *, username: str = "joao.silva"):
    role = Role(tenant_id=tenant.id, name="Caixa")
    db.add(role)
    db.commit()
    return create_tenant_user_account(
        db,
        tenant_id=UUID(str(tenant.id)),
        username=username,
        email=None,
        password="SenhaForte123",
        role_id=role.id,
        nome="Joao da Silva",
    )


def test_normalize_username_is_store_friendly_and_rejects_reserved_names():
    assert normalize_username("  João da Silva  ") == "joao.da.silva"
    try:
        normalize_username("admin")
    except UserAccountError as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Nome reservado deveria ser rejeitado")


def test_admin_can_create_username_only_account_per_tenant():
    db = _session()
    tenant = _tenant(db)
    user, role = _account(db, tenant)
    db.commit()

    assert user.email is None
    assert user.username == "joao.silva"
    assert verify_password("SenhaForte123", user.hashed_password)
    assert role.name == "Caixa"
    assert (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == UUID(str(tenant.id)),
        )
        .one()
        .role_id
        == role.id
    )


def test_service_keeps_legacy_email_only_account_compatible():
    db = _session()
    tenant = _tenant(db)
    role = Role(tenant_id=UUID(str(tenant.id)), name="Gestor")
    db.add(role)
    db.commit()

    user, _role = create_tenant_user_account(
        db,
        tenant_id=UUID(str(tenant.id)),
        username=None,
        email="gestor@loja.com",
        password="SenhaForte123",
        role_id=role.id,
    )
    db.commit()

    assert user.username is None
    assert user.email == "gestor@loja.com"


def test_same_username_can_exist_in_different_stores():
    db = _session()
    first_tenant = _tenant(db, name="Loja Um")
    first_user, _role = _account(db, first_tenant)
    db.commit()

    second_tenant = _tenant(db, name="Loja Dois")
    second_user, _role = _account(db, second_tenant)
    db.commit()

    assert first_user.username == second_user.username == "joao.silva"
    assert first_user.tenant_id != second_user.tenant_id


def test_login_schemas_keep_email_compatibility_and_accept_username():
    legacy = LoginRequest(email="dono@loja.com", password="segredo")
    username = LoginRequest(
        identifier="joao.silva",
        tenant="loja-teste",
        password="segredo",
    )
    mobile = EcommerceLoginRequest(identifier="joao.silva", password="segredo")

    assert legacy.identifier == "dono@loja.com"
    assert username.identifier == "joao.silva"
    assert mobile.identifier == "joao.silva"


def test_web_login_resolves_username_inside_informed_store(monkeypatch):
    db = _session()
    tenant = _tenant(db)
    user, _role = _account(db, tenant)
    db.commit()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    monkeypatch.setattr(
        "app.auth.auth_multitenant_account_routes.create_session",
        lambda **_kwargs: SimpleNamespace(token_jti="test-jti", expires_at=expires_at),
    )
    monkeypatch.setattr(
        "app.auth.auth_multitenant_account_routes._create_token_pair",
        lambda *_args: ("access-token", "refresh-token"),
    )
    monkeypatch.setattr(
        "app.auth.auth_multitenant_account_routes.register_successful_login",
        lambda *_args: None,
    )
    request = Request({"type": "http", "headers": []})

    response = login_multitenant(
        request=request,
        credentials=LoginRequest(
            identifier="joao.silva",
            tenant="loja-teste",
            password="SenhaForte123",
        ),
        db=db,
    )

    assert response.user["id"] == user.id
    assert response.user["username"] == "joao.silva"
    assert response.user["email"] is None
    assert response.tenants[0]["id"] == str(tenant.id)


def test_mobile_login_accepts_username_without_email(monkeypatch):
    db = _session()
    tenant = _tenant(db)
    user, _role = _account(db, tenant)
    db.commit()

    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._ensure_active_store_access",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public.register_successful_login",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._create_ecommerce_session_tokens",
        lambda *_args: {"access_token": "mobile-token", "token_type": "bearer"},
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._get_or_create_cliente_for_user",
        lambda *_args: SimpleNamespace(id=10),
    )
    monkeypatch.setattr(
        "app.routes.ecommerce_auth_public._serialize_profile",
        lambda target, *_args: {
            "id": target.id,
            "email": target.email,
            "username": target.username,
        },
    )
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-tenant-id", str(tenant.id).encode("ascii"))],
        }
    )

    response = login_cliente(
        payload=EcommerceLoginRequest(
            identifier="joao.silva",
            password="SenhaForte123",
        ),
        request=request,
        db=db,
    )

    assert response["access_token"] == "mobile-token"
    assert response["user"]["id"] == user.id
    assert response["user"]["email"] is None
    assert response["user"]["username"] == "joao.silva"


def test_admin_generated_password_updates_hash_and_returns_plaintext_once(monkeypatch):
    db = _session()
    tenant = _tenant(db)
    target_user, _role = _account(db, tenant)
    actor = User(
        tenant_id=tenant.id,
        email="admin@loja.com",
        username=None,
        hashed_password="irrelevante",
        nome="Admin",
        is_active=True,
        email_verified=True,
    )
    db.add(actor)
    db.commit()

    monkeypatch.setattr("app.usuarios_routes.revoke_all_sessions", lambda **_kwargs: 2)
    monkeypatch.setattr(
        "app.usuarios_routes.register_password_changed", lambda *_args: None
    )
    monkeypatch.setattr(
        "app.usuarios_routes.log_business_event", lambda **_kwargs: None
    )
    result = atualizar_credenciais_usuario.__wrapped__(
        user_id=target_user.id,
        payload=UserCredentialsUpdate(
            username="joao.silva",
            generate_password=True,
        ),
        db=db,
        user_and_tenant=(actor, UUID(str(tenant.id))),
    )

    assert result["password_changed"] is True
    assert result["sessions_revoked"] == 2
    assert result["generated_password"]
    assert verify_password(result["generated_password"], target_user.hashed_password)


def test_migration_makes_email_optional_and_username_unique_per_tenant():
    source = (REPO_ROOT / "alembic/versions/zxl20260828a1_username_login.py").read_text(
        encoding="utf-8"
    )

    assert 'down_revision = "zxk20260828a1"' in source
    assert 'sa.Column("username", sa.String(length=50), nullable=True)' in source
    assert '"email",' in source and "nullable=True" in source
    assert "uq_users_tenant_username" in source
    assert "email IS NOT NULL OR username IS NOT NULL" in source
