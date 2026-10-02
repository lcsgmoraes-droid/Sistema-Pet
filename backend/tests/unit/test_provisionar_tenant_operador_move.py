from argparse import Namespace
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import provisionar_tenant_operador as operator
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.models import Role, Tenant, User, UserSession, UserTenant
from app.tenancy.context import tenant_context


def test_move_creates_separate_login_and_preserves_historical_owner(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            User.__table__,
            Role.__table__,
            UserTenant.__table__,
            UserSession.__table__,
            EmpresaConfigGeral.__table__,
        ],
    )
    source_id = str(uuid4())
    with Session(engine) as db:
        db.add(
            Tenant(
                id=source_id,
                name="Vira Latas Andradina",
                cnpj="35205648000189",
                email="viralata.andradina@hotmail.com",
                plan="completo",
                billing_status="active",
            )
        )
        db.flush()
        with tenant_context(source_id):
            source_user = User(
                tenant_id=source_id,
                email="viralatatl067@gmail.com",
                nome="Silvio Rabelo",
                hashed_password="hash-existente",
                is_active=True,
                email_verified=True,
            )
            remaining_user = User(
                tenant_id=source_id,
                email="viralata.andradina@hotmail.com",
                nome="Mariana",
                hashed_password="hash-mariana",
                is_active=True,
                email_verified=True,
            )
            role = Role(tenant_id=source_id, name="Administrador")
            db.add_all([source_user, remaining_user, role])
            db.flush()
            source_user_id = source_user.id
            db.add_all(
                [
                    UserTenant(
                        user_id=source_user.id,
                        tenant_id=source_id,
                        role_id=role.id,
                        is_active=True,
                    ),
                    UserTenant(
                        user_id=remaining_user.id,
                        tenant_id=source_id,
                        role_id=role.id,
                        is_active=True,
                    ),
                ]
            )
            db.add(
                UserSession(
                    user_id=source_user_id,
                    tenant_id=UUID(source_id),
                    token_jti=str(uuid4()),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                    revoked=False,
                )
            )
            db.flush()
        db.commit()

        monkeypatch.setattr(operator, "sync_rls_auth_email", lambda *_: None)
        monkeypatch.setattr(operator, "sync_rls_tenant", lambda *_: None)
        monkeypatch.setattr(operator, "set_primary_tenant_login_name", lambda *_: None)
        monkeypatch.setattr(operator, "grant_all_permissions_to_role", lambda *_: 0)
        monkeypatch.setattr(
            operator, "create_default_roles_for_new_tenant", lambda *_: None
        )
        monkeypatch.setattr(operator, "onboard_tenant_defaults", lambda **_: None)

        args = Namespace(
            name="Casa de Racao Vira Lata - Tres Lagoas",
            login_name="Vira Lata Tres Lagoas",
            legal_name="Debora Cristina Valverde Farias",
            cnpj="17467592000159",
            email="viralatatl067@gmail.com",
            owner="Silvio Rabelo",
            address="Rua Marcilio Dias",
            number="843",
            bairro="Santa Rita",
            city="Tres Lagoas",
            uf="MS",
            cep="79620-250",
            phone=None,
            plan="same-as-source",
            move_existing_user_id=source_user_id,
            expected_source_tenant_id=source_id,
            expected_source_tenant_email="viralata.andradina@hotmail.com",
            expected_source_tenant_cnpj="35205648000189",
        )
        with tenant_context(source_id):
            assert db.get(User, source_user_id).email == args.email
            assert db.get(User, source_user_id).is_active is True
        result = operator.provisionar(db, args, password=None)

        old_user = db.get(User, source_user_id)
        new_user = db.get(User, result["user_id"])
        assert str(old_user.tenant_id) == source_id
        assert old_user.email is None and old_user.is_active is False
        assert old_user.hashed_password is None
        assert new_user.email == args.email
        assert new_user.hashed_password == "hash-existente"
        assert str(new_user.tenant_id) == result["tenant_id"]
        assert result["plan"] == "completo"
        assert result["billing_status"] == "active"
        assert db.scalars(select(UserSession)).one().revoked is True
        assert (
            db.scalars(
                select(UserTenant).where(
                    UserTenant.user_id == source_user_id,
                    UserTenant.is_active.is_(True),
                )
            ).first()
            is None
        )
        db.rollback()

        assert db.get(User, source_user_id).email == args.email
        assert db.scalars(select(UserSession)).one().revoked is False
        assert (
            db.scalars(select(Tenant).where(Tenant.cnpj == args.cnpj)).first() is None
        )

        db.get(Tenant, source_id).email = "outro@example.com"
        with pytest.raises(ValueError, match="Dados da empresa de origem divergentes"):
            operator.provisionar(db, args, password=None)
        db.rollback()
        assert db.get(User, source_user_id).is_active is True
