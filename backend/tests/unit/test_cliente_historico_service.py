from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models_cadastros import Cliente, ClienteHistoricoAlteracao
from app.veterinario_models import VetPartnerLink
from app.services.cliente_historico_service import registrar_alteracoes_cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant

LOJA = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            ClienteHistoricoAlteracao.__table__,
            Cliente.__table__,
            VetPartnerLink.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
        ],
    )
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_grava_so_os_campos_que_mudaram(db):
    antes = {"nome": "Ana", "telefone": "11911112222", "cidade": "Presidente Prudente"}
    depois = {"nome": "Ana Maria", "telefone": "11911112222", "cidade": "Presidente Prudente"}

    total = registrar_alteracoes_cliente(
        db, cliente_id=7, tenant_id=LOJA, user_id=3, antes=antes, depois=depois
    )
    db.commit()

    assert total == 1
    set_current_tenant(LOJA)
    linhas = db.query(ClienteHistoricoAlteracao).all()
    clear_current_tenant()
    assert len(linhas) == 1
    assert linhas[0].campo == "nome"
    assert linhas[0].valor_anterior == "Ana"
    assert linhas[0].valor_novo == "Ana Maria"
    assert linhas[0].user_id == 3
    assert linhas[0].cliente_id == 7


def test_ignora_campos_fora_da_lista_rastreada(db):
    total = registrar_alteracoes_cliente(
        db,
        cliente_id=7,
        tenant_id=LOJA,
        user_id=3,
        antes={"origem_cliente": "loja_fisica", "observacoes": "a"},
        depois={"origem_cliente": "ecommerce", "observacoes": "b"},
    )
    assert total == 0


def test_registra_troca_para_vazio_e_de_vazio_para_valor(db):
    total = registrar_alteracoes_cliente(
        db,
        cliente_id=7,
        tenant_id=LOJA,
        user_id=None,
        antes={"email": None, "celular": "11988887777"},
        depois={"email": "ana@x.com", "celular": None},
    )
    db.commit()

    assert total == 2
    set_current_tenant(LOJA)
    pares = {(l.campo, l.valor_anterior, l.valor_novo) for l in db.query(ClienteHistoricoAlteracao)}
    clear_current_tenant()
    assert ("email", None, "ana@x.com") in pares
    assert ("celular", "11988887777", None) in pares
