"""Garante o limite de seguranca central de user_loja_vinculo_service.py:
vincular um usuario a outra loja SO e permitido dentro do mesmo grupo
comercial — nunca a uma loja de outro cliente/grupo."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Role, Tenant, User, UserTenant
from app.services.user_loja_vinculo_service import (
    VinculoLojaError,
    desvincular_usuario_de_loja,
    listar_lojas_do_grupo_com_vinculo,
    vincular_usuario_a_loja_do_grupo,
    vincular_usuario_a_qualquer_loja_do_grupo,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant

TENANT_A1 = "11111111-1111-1111-1111-111111111111"
TENANT_A2 = "22222222-2222-2222-2222-222222222222"
TENANT_B1 = "33333333-3333-3333-3333-333333333333"


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            User.__table__,
            Role.__table__,
            UserTenant.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
        ],
    )
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _criar_tenant(db, tenant_id: str, nome: str):
    db.add(Tenant(id=tenant_id, name=nome, name_normalized=nome.lower()))


def _criar_role_e_vinculo(db, *, tenant_id: str, usuario_id: int, nome_role: str = "Vendedor"):
    set_current_tenant(tenant_id)
    role = Role(name=nome_role, tenant_id=tenant_id)
    db.add(role)
    db.flush()
    db.add(
        UserTenant(user_id=usuario_id, tenant_id=tenant_id, role_id=role.id, is_active=True)
    )
    db.flush()
    clear_current_tenant()
    return role


def _grupo(db, *, grupo_id_hint, criado_por_empresa_id, criado_por_usuario_id, lojas):
    grupo = GrupoComercial(
        nome=f"Grupo {grupo_id_hint}",
        criado_por_empresa_id=criado_por_empresa_id,
        criado_por_usuario_id=criado_por_usuario_id,
    )
    db.add(grupo)
    db.flush()
    for empresa_id in lojas:
        db.add(
            GrupoComercialMembro(
                grupo_id=grupo.id,
                empresa_id=empresa_id,
                papel="responsavel" if empresa_id == criado_por_empresa_id else "membro",
                status="ativo",
                usuario_referencia_id=criado_por_usuario_id,
            )
        )
    db.flush()
    return grupo


def _usuario(db, *, email: str, tenant_id: str):
    set_current_tenant(tenant_id)
    usuario = User(
        email=email,
        hashed_password="hash",
        nome=email,
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(usuario)
    db.flush()
    clear_current_tenant()
    return usuario


def test_vincula_usuario_a_outra_loja_do_mesmo_grupo(db):
    _criar_tenant(db, TENANT_A1, "Loja A1")
    _criar_tenant(db, TENANT_A2, "Loja A2")
    usuario = _usuario(db, email="titular@grupo-a.com", tenant_id=TENANT_A1)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A1, usuario_id=usuario.id)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A2, usuario_id=999999)  # so pra existir a Role
    _grupo(
        db,
        grupo_id_hint="A",
        criado_por_empresa_id=TENANT_A1,
        criado_por_usuario_id=usuario.id,
        lojas=[TENANT_A1, TENANT_A2],
    )
    db.commit()

    vinculo = vincular_usuario_a_loja_do_grupo(
        db,
        usuario=usuario,
        tenant_origem_id=TENANT_A1,
        tenant_destino_id=TENANT_A2,
    )

    assert str(vinculo.tenant_id) == TENANT_A2


def test_rejeita_vinculo_a_loja_de_outro_grupo_comercial(db):
    """O cenario central do receio: dado de um grupo comercial nao pode
    vazar/ser alcancado por usuario de outro grupo comercial."""
    _criar_tenant(db, TENANT_A1, "Loja A1")
    _criar_tenant(db, TENANT_B1, "Loja B1 (outro cliente)")
    usuario = _usuario(db, email="titular@grupo-a.com", tenant_id=TENANT_A1)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A1, usuario_id=usuario.id)

    # grupo A (so a loja A1) e grupo B (so a loja B1) - nunca se cruzam.
    _grupo(
        db,
        grupo_id_hint="A",
        criado_por_empresa_id=TENANT_A1,
        criado_por_usuario_id=usuario.id,
        lojas=[TENANT_A1],
    )
    outro_usuario = _usuario(db, email="titular@grupo-b.com", tenant_id=TENANT_B1)
    _grupo(
        db,
        grupo_id_hint="B",
        criado_por_empresa_id=TENANT_B1,
        criado_por_usuario_id=outro_usuario.id,
        lojas=[TENANT_B1],
    )
    db.commit()

    with pytest.raises(VinculoLojaError) as excinfo:
        vincular_usuario_a_loja_do_grupo(
            db,
            usuario=usuario,
            tenant_origem_id=TENANT_A1,
            tenant_destino_id=TENANT_B1,
        )

    assert excinfo.value.status_code == 403
    # raw SQL, sem contexto de tenant - so pra confirmar que nenhum
    # UserTenant foi criado pro usuario do grupo A na loja do grupo B.
    total = db.execute(
        text("SELECT count(*) FROM user_tenants WHERE user_id = :uid"),
        {"uid": usuario.id},
    ).scalar_one()
    assert total == 1  # so o vinculo original na loja de origem (A1)


def test_rejeita_usuario_sem_acesso_ativo_na_loja_de_origem(db):
    _criar_tenant(db, TENANT_A1, "Loja A1")
    _criar_tenant(db, TENANT_A2, "Loja A2")
    usuario = _usuario(db, email="sem-acesso@grupo-a.com", tenant_id=TENANT_A1)
    # Nenhum UserTenant criado para TENANT_A1 - usuario nao tem acesso ativo la.
    _grupo(
        db,
        grupo_id_hint="A",
        criado_por_empresa_id=TENANT_A1,
        criado_por_usuario_id=usuario.id,
        lojas=[TENANT_A1, TENANT_A2],
    )
    db.commit()

    with pytest.raises(VinculoLojaError) as excinfo:
        vincular_usuario_a_loja_do_grupo(
            db,
            usuario=usuario,
            tenant_origem_id=TENANT_A1,
            tenant_destino_id=TENANT_A2,
        )

    assert excinfo.value.status_code == 400


TENANT_A3 = "44444444-4444-4444-4444-444444444444"


def _grupo_abc(db, usuario):
    _criar_tenant(db, TENANT_A1, "Loja A1")
    _criar_tenant(db, TENANT_A2, "Loja A2")
    _criar_tenant(db, TENANT_A3, "Loja A3")
    _grupo(
        db,
        grupo_id_hint="A",
        criado_por_empresa_id=TENANT_A1,
        criado_por_usuario_id=usuario.id,
        lojas=[TENANT_A1, TENANT_A2, TENANT_A3],
    )


def test_lista_lojas_do_grupo_marca_vinculado_e_atual_corretamente(db):
    usuario = _usuario(db, email="titular@grupo-a.com", tenant_id=TENANT_A1)
    _grupo_abc(db, usuario)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A1, usuario_id=usuario.id)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A2, usuario_id=usuario.id)
    db.commit()

    lojas = listar_lojas_do_grupo_com_vinculo(
        db, tenant_origem_id=TENANT_A1, usuario_id=usuario.id
    )
    por_tenant = {loja["tenant_id"]: loja for loja in lojas}

    assert len(lojas) == 3
    assert por_tenant[TENANT_A1]["vinculado"] is True
    assert por_tenant[TENANT_A1]["atual"] is True
    assert por_tenant[TENANT_A2]["vinculado"] is True
    assert por_tenant[TENANT_A2]["atual"] is False
    assert por_tenant[TENANT_A3]["vinculado"] is False


def test_desvincula_usuario_de_loja_quando_sobra_pelo_menos_uma(db):
    usuario = _usuario(db, email="titular@grupo-a.com", tenant_id=TENANT_A1)
    _grupo_abc(db, usuario)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A1, usuario_id=usuario.id)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A2, usuario_id=usuario.id)
    db.commit()

    desvincular_usuario_de_loja(
        db, usuario=usuario, tenant_origem_id=TENANT_A1, tenant_destino_id=TENANT_A2
    )

    lojas = listar_lojas_do_grupo_com_vinculo(
        db, tenant_origem_id=TENANT_A1, usuario_id=usuario.id
    )
    por_tenant = {loja["tenant_id"]: loja for loja in lojas}
    assert por_tenant[TENANT_A2]["vinculado"] is False
    assert por_tenant[TENANT_A1]["vinculado"] is True  # a outra loja continua ativa


def test_rejeita_desvincular_a_ultima_loja_ativa_do_usuario(db):
    """O requisito central: usuario nunca pode ficar sem nenhuma loja."""
    usuario = _usuario(db, email="titular@grupo-a.com", tenant_id=TENANT_A1)
    _grupo_abc(db, usuario)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A1, usuario_id=usuario.id)
    db.commit()

    with pytest.raises(VinculoLojaError) as excinfo:
        desvincular_usuario_de_loja(
            db, usuario=usuario, tenant_origem_id=TENANT_A1, tenant_destino_id=TENANT_A1
        )

    assert excinfo.value.status_code == 400
    lojas = listar_lojas_do_grupo_com_vinculo(
        db, tenant_origem_id=TENANT_A1, usuario_id=usuario.id
    )
    assert any(loja["vinculado"] for loja in lojas)  # continua com pelo menos 1


def test_rejeita_desvincular_acesso_do_master_do_grupo_comercial(db):
    usuario = _usuario(db, email="master@grupo-a.com", tenant_id=TENANT_A1)
    usuario.master_grupo_id = 1
    _grupo_abc(db, usuario)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A1, usuario_id=usuario.id)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A2, usuario_id=usuario.id)
    db.commit()

    with pytest.raises(VinculoLojaError) as excinfo:
        desvincular_usuario_de_loja(
            db, usuario=usuario, tenant_origem_id=TENANT_A1, tenant_destino_id=TENANT_A2
        )

    assert excinfo.value.status_code == 403


def test_vincular_a_qualquer_loja_resolve_origem_sozinho(db):
    """Usuario so tem acesso ativo na A2 (nao na loja de quem esta operando,
    A1) — mesmo assim precisa dar pra vincular ele na A3, herdando o perfil
    da A2 automaticamente."""
    usuario = _usuario(db, email="titular@grupo-a.com", tenant_id=TENANT_A1)
    _grupo_abc(db, usuario)
    _criar_role_e_vinculo(db, tenant_id=TENANT_A2, usuario_id=usuario.id, nome_role="Gerente")
    _criar_role_e_vinculo(db, tenant_id=TENANT_A3, usuario_id=999999, nome_role="Gerente")
    db.commit()

    vinculo = vincular_usuario_a_qualquer_loja_do_grupo(
        db, usuario=usuario, tenant_destino_id=TENANT_A3
    )

    assert str(vinculo.tenant_id) == TENANT_A3
