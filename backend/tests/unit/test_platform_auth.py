from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.auth_multitenant_support import _hash_token
from app.auth.core import create_access_token, hash_password, verify_password
from app.db import get_session
from app.platform_auth import router as platform_auth_router
from app.platform_auth_models import PlatformAdmin, PlatformAdminSession
from app.routes.ops_tenants_routes import router as ops_tenants_router


def _test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PlatformAdmin.__table__.create(engine)
    PlatformAdminSession.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(platform_auth_router)
    app.include_router(ops_tenants_router)

    def override_session():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = override_session
    return app, session_factory


def _seed_admin(session_factory, password="senha-segura-123"):
    with session_factory() as db:
        admin = PlatformAdmin(
            email="dono@corepet.test",
            hashed_password=hash_password(password),
            name="Dono CorePet",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        return admin.id


def test_login_da_plataforma_usa_identidade_e_token_proprios():
    app, session_factory = _test_app()
    admin_id = _seed_admin(session_factory)

    with TestClient(app) as client:
        response = client.post(
            "/platform-auth/login",
            json={"email": "DONO@COREPET.TEST", "password": "senha-segura-123"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["admin"] == {
            "id": admin_id,
            "name": "Dono CorePet",
            "email": "dono@corepet.test",
            "scope": "platform_admin",
        }

        me = client.get(
            "/platform-auth/me",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["scope"] == "platform_admin"


def test_token_de_tenant_nao_acessa_corepet_ops():
    app, session_factory = _test_app()
    _seed_admin(session_factory)
    tenant_token = create_access_token(
        data={"sub": "1", "jti": "tenant-session", "tenant_id": "tenant-a"}
    )

    with TestClient(app) as client:
        response = client.get(
            "/admin/tenants",
            headers={"Authorization": f"Bearer {tenant_token}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Sessão administrativa inválida"


def test_recuperacao_altera_senha_e_revoga_sessoes(monkeypatch):
    app, session_factory = _test_app()
    admin_id = _seed_admin(session_factory)
    code = "123456"
    link_token = "token-seguro-da-plataforma-1234567890"
    stored = f"v2:{_hash_token(code)}:{_hash_token(link_token)}"
    monkeypatch.setattr(
        "app.platform_auth._issue_password_reset_tokens",
        lambda: (code, link_token, stored),
    )
    monkeypatch.setattr("app.platform_auth.send_email", lambda **_kwargs: True)

    with TestClient(app) as client:
        login = client.post(
            "/platform-auth/login",
            json={"email": "dono@corepet.test", "password": "senha-segura-123"},
        ).json()
        old_access_token = login["access_token"]

        requested = client.post(
            "/platform-auth/forgot-password",
            json={"email": "dono@corepet.test"},
        )
        assert requested.status_code == 200

        reset = client.post(
            "/platform-auth/reset-password",
            json={
                "email": "dono@corepet.test",
                "token": code,
                "nova_senha": "nova-senha-segura-456",
            },
        )
        assert reset.status_code == 200

        revoked = client.get(
            "/platform-auth/me",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )
        assert revoked.status_code == 401

    with session_factory() as db:
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
        assert verify_password("nova-senha-segura-456", admin.hashed_password)
        sessions = db.query(PlatformAdminSession).all()
        assert sessions and all(session.revoked for session in sessions)


def test_sessao_expirada_da_plataforma_e_rejeitada():
    app, session_factory = _test_app()
    admin_id = _seed_admin(session_factory)
    with session_factory() as db:
        session = PlatformAdminSession(
            platform_admin_id=admin_id,
            token_jti="expired-platform-session",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(session)
        db.commit()

    expired_token = create_access_token(
        data={
            "sub": f"platform:{admin_id}",
            "jti": "expired-platform-session",
            "scope": "platform_admin",
        }
    )
    with TestClient(app) as client:
        response = client.get(
            "/platform-auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
    assert response.status_code == 401
    assert "expirada" in response.json()["detail"]
