from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.models import Role, Tenant, User, UserTenant
from app.services.onboarding_credencial_service import (
    confirmar_credencial_repassada,
    confirmar_credenciais_do_usuario,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant, tenant_context

TENANT_1 = "11111111-1111-1111-1111-111111111111"
TENANT_2 = "22222222-2222-2222-2222-222222222222"
TENANT_3 = "33333333-3333-3333-3333-333333333333"


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Tenant.__table__, User.__table__, Role.__table__, UserTenant.__table__],
    )
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _tenant(db, tenant_id: str, *, pendente: bool):
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Loja {tenant_id[:4]}",
            name_normalized=f"loja {tenant_id[:4]}",
            onboarding_credencial_email_pendente=pendente,
        )
    )


def _usuario_com_vinculo(db, *, email: str, tenant_id: str, ativo: bool = True):
    set_current_tenant(tenant_id)
    usuario = User(email=email, hashed_password="hash", nome=email, is_active=True, tenant_id=tenant_id)
    db.add(usuario)
    db.flush()
    role = Role(name="Vendedor", tenant_id=tenant_id)
    db.add(role)
    db.flush()
    db.add(UserTenant(user_id=usuario.id, tenant_id=tenant_id, role_id=role.id, is_active=ativo))
    db.flush()
    clear_current_tenant()
    return usuario


def _vinculo(db, usuario, *, tenant_id: str, ativo: bool):
    set_current_tenant(tenant_id)
    role = Role(name="Vendedor", tenant_id=tenant_id)
    db.add(role)
    db.flush()
    db.add(UserTenant(user_id=usuario.id, tenant_id=tenant_id, role_id=role.id, is_active=ativo))
    db.flush()
    clear_current_tenant()


def _flag(db, tenant_id: str) -> bool:
    return db.query(Tenant).filter(Tenant.id == tenant_id).first().onboarding_credencial_email_pendente


def test_senha_definida_limpa_flag_apenas_das_lojas_com_acesso_ativo(db):
    _tenant(db, TENANT_1, pendente=True)
    _tenant(db, TENANT_2, pendente=True)
    _tenant(db, TENANT_3, pendente=True)
    titular = _usuario_com_vinculo(db, email="titular@grupo.com", tenant_id=TENANT_1)
    _vinculo(db, titular, tenant_id=TENANT_2, ativo=False)
    db.commit()

    limpas = confirmar_credenciais_do_usuario(db, user_id=titular.id)
    db.commit()

    assert limpas == 1
    assert _flag(db, TENANT_1) is False
    assert _flag(db, TENANT_2) is True
    assert _flag(db, TENANT_3) is True


def test_confirmacao_manual_limpa_so_a_loja_informada(db):
    _tenant(db, TENANT_1, pendente=True)
    _tenant(db, TENANT_2, pendente=True)
    db.commit()

    confirmar_credencial_repassada(db, tenant_id=TENANT_2)
    db.commit()

    assert _flag(db, TENANT_2) is False
    assert _flag(db, TENANT_1) is True


def test_confirmacao_manual_rejeita_loja_inexistente(db):
    with pytest.raises(LookupError):
        confirmar_credencial_repassada(db, tenant_id=TENANT_3)
