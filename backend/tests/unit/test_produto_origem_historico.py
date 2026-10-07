from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.produtos_catalogo_models import Produto, ProdutoHistoricoAlteracao
from app.veterinario_models import VetPartnerLink
from app.services.produto_historico_service import registrar_alteracoes_produto
from app.tenancy.context import clear_current_tenant, set_current_tenant


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            ProdutoHistoricoAlteracao.__table__,
            Produto.__table__,
            VetPartnerLink.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            GrupoComercialEstoqueCompartilhado.__table__,
        ],
    )
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_origem_do_produto_nao_pode_ser_trocada():
    loja = uuid4()
    produto = Produto(tenant_id=loja, nome="Racao", codigo="SKU1")
    produto.origem_tenant_id = loja
    with pytest.raises(ValueError):
        produto.origem_tenant_id = uuid4()


def test_historico_registra_so_campos_base_alterados(db):
    loja = uuid4()
    total = registrar_alteracoes_produto(
        db,
        produto_id=5,
        tenant_id=loja,
        user_id=2,
        antes={"nome": "Racao A", "codigo_barras": "789", "preco_venda": 10.0},
        depois={"nome": "Racao B", "codigo_barras": "789", "preco_venda": 12.0},
    )
    db.commit()

    assert total == 1
    set_current_tenant(loja)
    registro = db.query(ProdutoHistoricoAlteracao).one()
    clear_current_tenant()
    assert (registro.campo, registro.valor_anterior, registro.valor_novo) == ("nome", "Racao A", "Racao B")
    assert registro.user_id == 2
