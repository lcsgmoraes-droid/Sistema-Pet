"""Codigos unicos no grupo comercial: pessoa e SKU de produto.

Roda no Postgres de desenvolvimento dentro de uma transacao revertida.
"""

import os
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.clientes.common import gerar_codigo_cliente
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Tenant
from app.models_cadastros import Cliente
from app.produtos.validators import _validar_sku_unico
from app.produtos_catalogo_models import Produto
from app.tenancy.context import clear_current_tenant, set_current_tenant

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith("postgresql"),
    reason="validacao de grupo so roda em Postgres",
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


def _produto(session, loja, codigo):
    set_current_tenant(loja)
    usuario = session.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    session.add(Produto(tenant_id=UUID(loja), user_id=usuario, nome="Racao", codigo=codigo, tipo_produto="simples", tipo="produto", is_parent=False))
    session.flush()
    clear_current_tenant()


def test_codigo_de_pessoa_nao_se_repete_entre_lojas_do_grupo(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    _grupo(sessao, [loja_a, loja_b])
    usuario = sessao.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()

    set_current_tenant(loja_a)
    codigo_a = gerar_codigo_cliente(sessao, "PF", UUID(loja_a))
    sessao.add(Cliente(tenant_id=UUID(loja_a), origem_tenant_id=UUID(loja_a), user_id=usuario, codigo=codigo_a, nome="A", is_cliente=True))
    sessao.flush()

    set_current_tenant(loja_b)
    codigo_b = gerar_codigo_cliente(sessao, "PF", UUID(loja_b))
    assert codigo_b != codigo_a
    assert int(codigo_b) > int(codigo_a)


def test_sku_de_produto_ja_usado_em_outra_loja_do_grupo_e_recusado(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    _grupo(sessao, [loja_a, loja_b])
    _produto(sessao, loja_a, "SKU-GRP-1")

    set_current_tenant(loja_b)
    with pytest.raises(HTTPException) as excinfo:
        _validar_sku_unico(sessao, "sku-grp-1", UUID(loja_b))
    assert excinfo.value.status_code == 400


def test_sku_livre_no_grupo_passa(sessao):
    loja_a = _loja(sessao, "Loja A")
    loja_fora = _loja(sessao, "Loja de fora")
    _grupo(sessao, [loja_a])
    _produto(sessao, loja_a, "SKU-GRP-1")
    set_current_tenant(loja_fora)
    _validar_sku_unico(sessao, "SKU-LIVRE", UUID(loja_fora))


def test_codigo_de_barras_ja_usado_em_outra_loja_do_grupo_e_recusado(sessao):
    from app.produtos.validators import _validar_codigo_barras_unico

    loja_a = _loja(sessao, "Loja A")
    loja_b = _loja(sessao, "Loja B")
    _grupo(sessao, [loja_a, loja_b])
    set_current_tenant(loja_a)
    usuario = sessao.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    sessao.add(Produto(tenant_id=UUID(loja_a), user_id=usuario, nome="Racao", codigo="BAR-1", codigo_barras="7891234567890", tipo_produto="simples", tipo="produto", is_parent=False))
    sessao.flush()
    clear_current_tenant()

    set_current_tenant(loja_b)
    with pytest.raises(HTTPException) as excinfo:
        _validar_codigo_barras_unico(sessao, "7891234567890", UUID(loja_b))
    assert excinfo.value.status_code == 400
