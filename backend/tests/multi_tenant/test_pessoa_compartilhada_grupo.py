"""Pessoa cadastrada por uma loja do grupo comercial fica visivel para as demais
lojas ativas do mesmo grupo, e nao para lojas de fora dele.

Roda no Postgres de desenvolvimento dentro de uma transacao que e revertida no
fim, sem deixar dados no banco. O filtro de leitura por grupo so atua em Postgres.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Tenant
from app.models_cadastros import Cliente, Pet
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


def _grupo_com_lojas(session, lojas):
    grupo = GrupoComercial(
        nome="Grupo teste",
        criado_por_empresa_id=lojas[0],
        criado_por_usuario_id=1,
    )
    session.add(grupo)
    session.flush()
    for loja in lojas:
        session.add(GrupoComercialMembro(grupo_id=grupo.id, empresa_id=loja, status="ativo"))
        session.flush()
    return grupo


def _usuario_existente(session):
    return session.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()


def _pessoa(session, tenant_id, nome):
    set_current_tenant(tenant_id)
    cliente = Cliente(
        tenant_id=tenant_id,
        origem_tenant_id=tenant_id,
        user_id=_usuario_existente(session),
        nome=nome,
        is_cliente=True,
    )
    session.add(cliente)
    session.flush()
    clear_current_tenant()
    return cliente


def test_pessoa_de_uma_loja_aparece_para_as_demais_do_grupo(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    loja_fora = _loja(sessao, "Loja de fora")
    _grupo_com_lojas(sessao, [loja_a, loja_b])
    pessoa = _pessoa(sessao, loja_a, "Maria do grupo")
    sessao.commit()

    set_current_tenant(loja_b)
    visiveis = {c.id for c in sessao.query(Cliente).filter(Cliente.id == pessoa.id).all()}
    assert pessoa.id in visiveis

    set_current_tenant(loja_fora)
    visiveis_fora = {c.id for c in sessao.query(Cliente).filter(Cliente.id == pessoa.id).all()}
    assert pessoa.id not in visiveis_fora


def test_loja_do_grupo_pode_editar_pessoa_de_outra_loja(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    _grupo_com_lojas(sessao, [loja_a, loja_b])
    pessoa = _pessoa(sessao, loja_a, "Nome antigo")
    sessao.commit()

    set_current_tenant(loja_b)
    registro = sessao.query(Cliente).filter(Cliente.id == pessoa.id).one()
    registro.nome = "Nome novo"
    sessao.commit()

    sessao.expire_all()
    assert sessao.query(Cliente).filter(Cliente.id == pessoa.id).one().nome == "Nome novo"


def test_grupo_inativo_nao_compartilha(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    grupo = _grupo_com_lojas(sessao, [loja_a, loja_b])
    grupo.status = "inativo"
    pessoa = _pessoa(sessao, loja_a, "Pessoa")
    sessao.commit()

    set_current_tenant(loja_b)
    visiveis = {c.id for c in sessao.query(Cliente).filter(Cliente.id == pessoa.id).all()}
    assert pessoa.id not in visiveis


def test_pet_de_uma_loja_aparece_para_as_demais_do_grupo(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    loja_fora = _loja(sessao, "Loja de fora")
    _grupo_com_lojas(sessao, [loja_a, loja_b])
    tutor = _pessoa(sessao, loja_a, "Tutor do grupo")
    set_current_tenant(loja_a)
    pet = Pet(
        tenant_id=loja_a,
        origem_tenant_id=loja_a,
        cliente_id=tutor.id,
        user_id=_usuario_existente(sessao),
        codigo=f"PET-{uuid4().hex[:8]}",
        nome="Rex",
        especie="cao",
    )
    sessao.add(pet)
    sessao.flush()
    clear_current_tenant()
    sessao.commit()

    set_current_tenant(loja_b)
    assert pet.id in {p.id for p in sessao.query(Pet).filter(Pet.id == pet.id).all()}
    set_current_tenant(loja_fora)
    assert pet.id not in {p.id for p in sessao.query(Pet).filter(Pet.id == pet.id).all()}
