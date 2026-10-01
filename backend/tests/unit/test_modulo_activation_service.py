from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata.
from app.models import AssinaturaModulo, AuditLog, Tenant
from app.services.modulo_activation_service import (
    ModuloActivationError,
    ativar_modulo_manual,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant

MODULOS_PREMIUM = frozenset(["banho_tosa", "veterinario"])


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[Tenant.__table__, AssinaturaModulo.__table__, AuditLog.__table__],
    )
    session = Session(engine)
    tenant_id = "11111111-1111-1111-1111-111111111111"
    session.add(Tenant(id=tenant_id, name="Loja Teste", name_normalized="loja teste"))
    session.commit()
    set_current_tenant(UUID(tenant_id))
    try:
        yield session, tenant_id
    finally:
        session.close()
        clear_current_tenant()


def _contar(db, tabela: str, condicao: str = "1=1", **params) -> int:
    return db.execute(text(f"SELECT count(*) FROM {tabela} WHERE {condicao}"), params).scalar_one()


def _hex(tenant_id: str) -> str:
    # AssinaturaModulo.tenant_id usa UUID(as_uuid=True), armazenado no SQLite
    # como hex sem hifens (32 chars) - diferente de Tenant.id (String(36)).
    return tenant_id.replace("-", "")


def test_ativar_modulo_manual_modulo_invalido_levanta_erro(db):
    session, tenant_id = db
    tenant = session.query(Tenant).filter(Tenant.id == tenant_id).one()

    with pytest.raises(ModuloActivationError) as excinfo:
        ativar_modulo_manual(
            session,
            tenant=tenant,
            modulo="modulo-que-nao-existe",
            modulos_premium=MODULOS_PREMIUM,
            ativado_por_user_id=None,
        )

    assert excinfo.value.status_code == 400


def test_ativar_modulo_manual_cria_assinatura_e_atualiza_modulos_ativos(db):
    session, tenant_id = db
    tenant = session.query(Tenant).filter(Tenant.id == tenant_id).one()

    resultado = ativar_modulo_manual(
        session,
        tenant=tenant,
        modulo="banho_tosa",
        modulos_premium=MODULOS_PREMIUM,
        ativado_por_user_id=None,
    )

    assert resultado == {"ok": True, "modulo": "banho_tosa", "tenant_id": tenant_id}
    assert "banho_tosa" in tenant.modulos_ativos
    assert (
        _contar(
            session,
            "assinaturas_modulos",
            "tenant_id = :tid AND modulo = 'banho_tosa' AND status = 'ativo'",
            tid=_hex(tenant_id),
        )
        == 1
    )


def test_ativar_modulo_manual_chamada_duplicada_nao_duplica_assinatura(db):
    session, tenant_id = db
    tenant = session.query(Tenant).filter(Tenant.id == tenant_id).one()

    for _ in range(2):
        ativar_modulo_manual(
            session,
            tenant=tenant,
            modulo="veterinario",
            modulos_premium=MODULOS_PREMIUM,
            ativado_por_user_id=None,
        )

    assert (
        _contar(
            session,
            "assinaturas_modulos",
            "tenant_id = :tid AND modulo = 'veterinario' AND status = 'ativo'",
            tid=_hex(tenant_id),
        )
        == 1
    )


def test_ativar_modulo_manual_commit_false_nao_commita(db):
    session, tenant_id = db
    tenant = session.query(Tenant).filter(Tenant.id == tenant_id).one()

    ativar_modulo_manual(
        session,
        tenant=tenant,
        modulo="banho_tosa",
        modulos_premium=MODULOS_PREMIUM,
        ativado_por_user_id=None,
        commit=False,
    )
    session.rollback()

    assert _contar(session, "assinaturas_modulos", "tenant_id = :tid", tid=_hex(tenant_id)) == 0
