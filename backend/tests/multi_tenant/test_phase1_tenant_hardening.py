from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.produtos_models import Produto
from app.tenancy.context import clear_current_tenant, set_current_tenant


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Produto.__table__.create(engine, checkfirst=True)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def _produto(codigo="SKU-TESTE", nome="Produto teste", tenant_id=None):
    return Produto(
        tenant_id=tenant_id,
        user_id=1,
        codigo=codigo,
        nome=nome,
        preco_venda=10.0,
        estoque_atual=1,
    )


def test_query_produto_sem_tenant_no_contexto_falha(db_session):
    tenant_id = uuid4()
    set_current_tenant(tenant_id)
    db_session.add(_produto(codigo="SKU-A"))
    db_session.commit()

    clear_current_tenant()

    with pytest.raises(RuntimeError, match="multi-tenant"):
        db_session.query(Produto).all()


def test_query_produto_com_tenant_retorna_apenas_dados_do_contexto(db_session):
    tenant_1 = uuid4()
    tenant_2 = uuid4()

    set_current_tenant(tenant_1)
    db_session.add(_produto(codigo="SKU-T1", nome="Produto tenant 1"))
    db_session.commit()

    set_current_tenant(tenant_2)
    db_session.add(_produto(codigo="SKU-T2", nome="Produto tenant 2"))
    db_session.commit()

    set_current_tenant(tenant_1)
    produtos = db_session.query(Produto).all()

    assert len(produtos) == 1
    assert produtos[0].codigo == "SKU-T1"
    assert produtos[0].tenant_id == tenant_1


def test_insert_produto_sem_tenant_no_contexto_falha(db_session):
    clear_current_tenant()
    db_session.add(_produto(codigo="SKU-SEM-TENANT"))

    with pytest.raises(RuntimeError, match="sem tenant_id no contexto"):
        db_session.flush()


def test_insert_produto_com_tenant_no_contexto_recebe_tenant_id(db_session):
    tenant_id = uuid4()
    set_current_tenant(tenant_id)

    produto = _produto(codigo="SKU-AUTO-TENANT")
    db_session.add(produto)
    db_session.flush()

    assert produto.tenant_id == tenant_id


def test_insert_produto_com_tenant_diferente_do_contexto_falha(db_session):
    tenant_contexto = uuid4()
    tenant_objeto = uuid4()
    set_current_tenant(tenant_contexto)

    db_session.add(_produto(codigo="SKU-TENANT-ERRADO", tenant_id=tenant_objeto))

    with pytest.raises(RuntimeError, match="tenant_id diferente do contexto"):
        db_session.flush()
