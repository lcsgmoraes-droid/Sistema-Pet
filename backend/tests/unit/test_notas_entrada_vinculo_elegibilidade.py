from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app import produto_identidade_models  # noqa: F401
from app.notas_entrada import itens_produto_routes as routes
from app.produtos_models import NotaEntrada, NotaEntradaItem, Produto
from app.tenancy.context import clear_current_tenant, set_current_tenant


@pytest.fixture
def contexto(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for model in (NotaEntrada, NotaEntradaItem, Produto):
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    tenant = uuid4()
    set_current_tenant(tenant)
    with Session(engine) as db:
        nota = NotaEntrada(
            tenant_id=tenant,
            user_id=1,
            numero_nota="FICTICIA",
            serie="1",
            chave_acesso="1" * 44,
            fornecedor_cnpj="00000000000000",
            fornecedor_nome="Fornecedor ficticio",
            data_emissao=datetime(2026, 10, 26),
            valor_produtos=10,
            valor_total=10,
            xml_content="<xml/>",
            produtos_nao_vinculados=1,
        )
        db.add(nota)
        db.flush()
        item = NotaEntradaItem(
            tenant_id=tenant,
            nota_entrada_id=nota.id,
            numero_item=1,
            descricao="Item ficticio",
            quantidade=1,
            valor_unitario=10,
            valor_total=10,
        )
        db.add(item)
        db.flush()
        monkeypatch.setattr(
            routes, "_aplicar_dados_fiscais_item_no_produto", lambda *_: False
        )
        monkeypatch.setattr(
            routes, "_aplicar_codigos_barras_item_no_produto", lambda *_: None
        )
        monkeypatch.setattr(routes, "calcular_composicao_custos_nota", lambda *_: {})
        try:
            yield db, tenant, nota, item
        finally:
            db.rollback()
            clear_current_tenant()
    engine.dispose()


@pytest.mark.parametrize("tipo", ["SIMPLES", "VARIACAO", "PAI", "KIT"])
def test_vinculo_xml_aceita_so_simples_ou_variacao_antes_de_alterar_item(
    contexto, tipo
):
    db, tenant, nota, item = contexto
    produto = Produto(
        user_id=1,
        tenant_id=tenant,
        codigo=f"F-{tipo}",
        nome="Produto ficticio",
        tipo_produto=tipo,
    )
    db.add(produto)
    db.flush()
    if tipo in {"PAI", "KIT"}:
        with pytest.raises(HTTPException) as erro:
            routes.vincular_produto(
                nota.id, item.id, produto.id, db, (SimpleNamespace(id=1), tenant)
            )
        assert erro.value.status_code == 400
        assert not item.vinculado and item.produto_id is None
        assert nota.produtos_nao_vinculados == 1
        assert not db.dirty
    else:
        resultado = routes.vincular_produto(
            nota.id, item.id, produto.id, db, (SimpleNamespace(id=1), tenant)
        )
        assert resultado["produto_id"] == produto.id
        assert item.vinculado and item.produto_id == produto.id


def test_vinculo_xml_nao_aceita_produto_de_outra_empresa(contexto):
    db, tenant, nota, item = contexto
    outro_tenant = uuid4()
    set_current_tenant(outro_tenant)
    produto = Produto(
        user_id=1,
        tenant_id=outro_tenant,
        codigo="FORA",
        nome="Produto de outra empresa",
        tipo_produto="SIMPLES",
    )
    db.add(produto)
    db.flush()
    produto_id = produto.id
    set_current_tenant(tenant)
    with pytest.raises(HTTPException) as erro:
        routes.vincular_produto(
            nota.id, item.id, produto_id, db, (SimpleNamespace(id=1), tenant)
        )
    assert erro.value.status_code == 404
    assert not item.vinculado and item.produto_id is None
