"""Registros clinicos do pet: leitura pelo grupo, escrita so pela loja que registrou.

Roda no Postgres de desenvolvimento dentro de uma transacao revertida.
"""

import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Tenant
from app.models_cadastros import Cliente, Pet, PetRegistroClinico
from app.services import pet_registros_clinicos_service as servico
from app.tenancy.context import clear_current_tenant, set_current_tenant

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith("postgresql"),
    reason="filtro de grupo comercial so atua em Postgres",
)


@pytest.fixture()
def sessao():
    engine = create_engine(DATABASE_URL)
    conexao = engine.connect()
    transacao = conexao.begin()
    session = Session(bind=conexao)
    try:
        yield session
    finally:
        session.close()
        transacao.rollback()
        conexao.close()
        engine.dispose()
        clear_current_tenant()


def _loja(session, nome):
    tenant_id = str(uuid4())
    session.add(Tenant(id=tenant_id, name=nome, name_normalized=nome.lower(), status="active"))
    session.flush()
    return tenant_id


def _grupo(session, lojas):
    grupo = GrupoComercial(nome="Grupo teste", criado_por_empresa_id=lojas[0], criado_por_usuario_id=1)
    session.add(grupo)
    session.flush()
    for loja in lojas:
        session.add(GrupoComercialMembro(grupo_id=grupo.id, empresa_id=loja, status="ativo"))
        session.flush()


def _usuario(session):
    return session.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()


def _pet(session, loja):
    set_current_tenant(loja)
    tutor = Cliente(tenant_id=loja, origem_tenant_id=loja, user_id=_usuario(session), nome="Tutor", is_cliente=True)
    session.add(tutor)
    session.flush()
    pet = Pet(
        tenant_id=loja,
        origem_tenant_id=loja,
        cliente_id=tutor.id,
        user_id=_usuario(session),
        codigo=f"PET-{uuid4().hex[:8]}",
        nome="Rex",
        especie="cao",
    )
    session.add(pet)
    session.flush()
    pet_id = pet.id
    clear_current_tenant()
    return pet_id


def test_registro_da_loja_a_aparece_para_loja_b_do_grupo(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    _grupo(sessao, [loja_a, loja_b])
    set_current_tenant(loja_a)
    pet_id = _pet(sessao, loja_a)
    set_current_tenant(loja_a)
    servico.criar_registro(sessao, pet_id=pet_id, tenant_id=loja_a, user_id=None, tipo="historico", texto="Vacina V10")
    sessao.commit()

    set_current_tenant(loja_b)
    assert servico.pet_visivel(sessao, pet_id, loja_b) is not None
    registros = servico.listar_registros(sessao, pet_id, "historico")
    assert [r.texto for r in registros] == ["Vacina V10"]


def test_loja_de_fora_do_grupo_nao_ve_o_pet(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_fora = _loja(sessao, "Loja de fora")
    _grupo(sessao, [loja_a])
    pet_id = _pet(sessao, loja_a)
    set_current_tenant(loja_a)
    sessao.commit()

    set_current_tenant(loja_fora)
    assert servico.pet_visivel(sessao, pet_id, loja_fora) is None


def test_so_a_loja_que_registrou_pode_apagar(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    _grupo(sessao, [loja_a, loja_b])
    set_current_tenant(loja_a)
    pet_id = _pet(sessao, loja_a)
    set_current_tenant(loja_a)
    registro = servico.criar_registro(sessao, pet_id=pet_id, tenant_id=loja_a, user_id=None, tipo="peso", valor=5.2)
    sessao.commit()

    with pytest.raises(HTTPException) as excinfo:
        servico.excluir_registro(sessao, registro_id=registro.id, pet_id=pet_id, tenant_id=loja_b)
    assert excinfo.value.status_code == 403
    set_current_tenant(loja_a)
    assert sessao.query(PetRegistroClinico).filter_by(id=registro.id).count() == 1


def test_valor_igual_ao_anterior_nao_gera_registro_novo(sessao):
    loja_a = _loja(sessao, "Loja A")
    _grupo(sessao, [loja_a])
    set_current_tenant(loja_a)
    pet_id = _pet(sessao, loja_a)
    set_current_tenant(loja_a)
    primeiro = servico.registrar_se_mudou(sessao, pet_id=pet_id, tenant_id=loja_a, user_id=None, tipo="peso", novo=4.0)
    repetido = servico.registrar_se_mudou(sessao, pet_id=pet_id, tenant_id=loja_a, user_id=None, tipo="peso", novo=4.0)
    mudou = servico.registrar_se_mudou(sessao, pet_id=pet_id, tenant_id=loja_a, user_id=None, tipo="peso", novo=4.3)
    sessao.commit()

    assert primeiro is not None
    assert repetido is None
    assert mudou is not None
    set_current_tenant(loja_a)
    assert sessao.query(PetRegistroClinico).filter_by(pet_id=pet_id, tipo="peso").count() == 2
