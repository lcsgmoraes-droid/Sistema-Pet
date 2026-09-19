import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.services.tenant_provisioning_service as tenant_provisioning_service
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata (evita
# InvalidRequestError ao resolver relationship() por nome de outras classes,
# mesmo criando so um subconjunto de tabelas abaixo).
from app.models import Permission, Role, RolePermission, Tenant, TenantLoginName, User, UserTenant
from app.services.default_roles_service import DEFAULT_TENANT_ROLES
from app.services.tenant_provisioning_service import (
    TenantOnboardingError,
    provision_tenant,
)
from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant


TENANT_EXISTENTE = uuid.UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            TenantLoginName.__table__,
            User.__table__,
            Role.__table__,
            Permission.__table__,
            RolePermission.__table__,
            UserTenant.__table__,
        ],
    )
    session = Session(engine)
    monkeypatch.setattr(
        tenant_provisioning_service,
        "onboard_tenant_defaults",
        lambda **_kwargs: {"created": {}},
    )
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def test_provision_tenant_cria_usuario_novo_tenant_e_roles_e_limpa_contexto(db):
    resultado = provision_tenant(
        db,
        tenant_name="Loja Nova",
        login_name="Loja Nova",
        plan_code="pet-start",
        organization_type=None,
        new_user_email="dono@example.com",
        new_user_password="segredo123",
        new_user_nome="Dono da Loja",
    )
    db.commit()

    assert resultado.created_new_user is True
    assert resultado.tenant.name == "Loja Nova"
    assert resultado.login_name == "Loja Nova"

    # sem restore_tenant_id -> contexto e limpo no final, nao deixa vazamento
    # pro proximo objeto criado fora dessa chamada.
    assert get_current_tenant() is None

    # consultas em tabelas multi-tenant exigem contexto ativo (fail-fast do
    # ORM) - simula o que uma rota faria depois, ja re-autenticada no tenant.
    set_current_tenant(resultado.tenant_id)
    usuario = db.query(User).filter(User.email == "dono@example.com").one()
    assert usuario.id == resultado.user.id
    assert usuario.tenant_id == resultado.tenant_id

    roles = db.query(Role).filter(Role.tenant_id == resultado.tenant_id).all()
    assert {role.name for role in roles} == {"Administrador", *DEFAULT_TENANT_ROLES.keys()}

    vinculo = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == usuario.id, UserTenant.tenant_id == resultado.tenant_id)
        .one()
    )
    assert vinculo.role_id == resultado.admin_role.id
    assert vinculo.is_active is True


def test_provision_tenant_reaproveita_usuario_existente_e_restaura_contexto(db):
    # simula uma requisicao ja autenticada no tenant chamador - e nesse
    # contexto que adicionar_loja() invoca provision_tenant() na pratica.
    set_current_tenant(TENANT_EXISTENTE)
    db.add(
        Tenant(
            id=str(TENANT_EXISTENTE),
            name="Loja Chamadora",
            name_normalized="loja chamadora",
        )
    )
    usuario_existente = User(
        email="titular@example.com",
        hashed_password="hash",
        nome="Titular",
        tenant_id=TENANT_EXISTENTE,
        is_active=True,
    )
    db.add(usuario_existente)
    db.commit()

    resultado = provision_tenant(
        db,
        tenant_name="Segunda Loja",
        login_name="Segunda Loja",
        plan_code="pet-start",
        organization_type=None,
        user=usuario_existente,
        restore_tenant_id=TENANT_EXISTENTE,
    )
    db.commit()

    assert resultado.created_new_user is False
    assert resultado.user.id == usuario_existente.id

    # restore_tenant_id informado -> contexto volta pro tenant chamador, em
    # vez de ficar limpo (quem chamou continua autenticado nele).
    assert get_current_tenant() == TENANT_EXISTENTE

    # nao duplicou o usuario - so criou um UserTenant novo ligando o mesmo
    # usuario ao tenant novo. Consulta pelo contexto do tenant chamador,
    # onde o usuario "mora" (User.tenant_id).
    total_usuarios = db.query(User).filter(User.email == "titular@example.com").count()
    assert total_usuarios == 1

    # o vinculo novo pertence ao tenant NOVO - precisa do contexto dele pra
    # ser visivel (o guard filtra toda query multi-tenant pelo contexto ativo).
    set_current_tenant(resultado.tenant_id)
    vinculo_novo = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == usuario_existente.id,
            UserTenant.tenant_id == resultado.tenant_id,
        )
        .one()
    )
    assert vinculo_novo.role_id == resultado.admin_role.id


def test_provision_tenant_exige_user_ou_credenciais_de_usuario_novo(db):
    with pytest.raises(ValueError):
        provision_tenant(
            db,
            tenant_name="Loja Sem Dono",
            login_name="Loja Sem Dono",
            plan_code="pet-start",
            organization_type=None,
        )


def test_provision_tenant_propaga_falha_de_onboarding_como_tenant_onboarding_error(
    db, monkeypatch
):
    monkeypatch.setattr(
        tenant_provisioning_service,
        "onboard_tenant_defaults",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("template indisponivel")),
    )

    with pytest.raises(TenantOnboardingError):
        provision_tenant(
            db,
            tenant_name="Loja Com Falha",
            login_name="Loja Com Falha",
            plan_code="pet-start",
            organization_type=None,
            new_user_email="falha@example.com",
            new_user_password="segredo123",
            new_user_nome="Usuario Falha",
        )

    # mesmo com erro, o finally roda e limpa o contexto (sem restore_tenant_id).
    assert get_current_tenant() is None
