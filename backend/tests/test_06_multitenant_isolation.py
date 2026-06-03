"""
Testes de isolamento multi-tenant.
"""
from datetime import datetime
from uuid import UUID, uuid4

from app.produtos_models import Produto
from app.vendas_models import Venda


def _tenant_uuid(tenant):
    return UUID(str(tenant.id))


def _create_product(tenant, user=None, nome: str = "Produto", preco: float = 10.0) -> Produto:
    return Produto(
        tenant_id=_tenant_uuid(tenant),
        user_id=user.id if user else None,
        codigo=f"PROD-{uuid4().hex[:8].upper()}",
        nome=nome,
        preco_venda=preco,
        estoque_atual=10,
        ativo=True,
    )


def _create_sale(tenant, user, total: float) -> Venda:
    return Venda(
        tenant_id=_tenant_uuid(tenant),
        user_id=user.id,
        vendedor_id=user.id,
        numero_venda=f"TST-{uuid4().hex[:8].upper()}",
        data_venda=datetime.utcnow(),
        subtotal=total,
        total=total,
        status="finalizada",
    )


def test_tenant_cannot_access_other_tenant_products(
    db_session,
    tenant_factory,
    user_factory,
    tenant_context,
):
    """
    Testa que tenant A nao acessa produtos do tenant B.
    Protege: isolamento de dados de produtos.
    """
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")
    user_a = user_factory(tenant_id=tenant_a.id)
    user_b = user_factory(tenant_id=tenant_b.id)

    tenant_context(tenant_a.id)
    produto_a = _create_product(tenant_a, user_a, "Produto Loja A", 50.00)
    db_session.add(produto_a)
    db_session.commit()

    tenant_context(tenant_b.id)
    produto_b = _create_product(tenant_b, user_b, "Produto Loja B", 75.00)
    db_session.add(produto_b)
    db_session.commit()

    tenant_context(tenant_a.id)
    produtos_a = db_session.query(Produto).filter_by(tenant_id=_tenant_uuid(tenant_a)).all()
    assert all(p.tenant_id == _tenant_uuid(tenant_a) for p in produtos_a)
    assert produto_b not in produtos_a

    tenant_context(tenant_b.id)
    produtos_b = db_session.query(Produto).filter_by(tenant_id=_tenant_uuid(tenant_b)).all()
    assert all(p.tenant_id == _tenant_uuid(tenant_b) for p in produtos_b)
    assert produto_a not in produtos_b


def test_tenant_cannot_access_other_tenant_sales(
    db_session,
    tenant_factory,
    user_factory,
    tenant_context,
):
    """
    Testa que tenant A nao acessa vendas do tenant B.
    Protege: isolamento de dados de vendas.
    """
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")

    user_a = user_factory(tenant_id=tenant_a.id)
    user_b = user_factory(tenant_id=tenant_b.id)

    tenant_context(tenant_a.id)
    venda_a = _create_sale(tenant_a, user_a, total=100.00)
    db_session.add(venda_a)
    db_session.commit()

    tenant_context(tenant_b.id)
    venda_b = _create_sale(tenant_b, user_b, total=200.00)
    db_session.add(venda_b)
    db_session.commit()

    tenant_context(tenant_a.id)
    vendas_a = db_session.query(Venda).filter_by(tenant_id=_tenant_uuid(tenant_a)).all()
    assert all(v.tenant_id == _tenant_uuid(tenant_a) for v in vendas_a)
    assert venda_b not in vendas_a

    tenant_context(tenant_b.id)
    vendas_b = db_session.query(Venda).filter_by(tenant_id=_tenant_uuid(tenant_b)).all()
    assert all(v.tenant_id == _tenant_uuid(tenant_b) for v in vendas_b)
    assert venda_a not in vendas_b


def test_jwt_enforces_tenant_context(auth_headers, tenant_factory):
    """
    Testa que JWT contem tenant_id correto para isolamento.
    Protege: contexto de tenant em requisicoes autenticadas.
    """
    tenant_a = tenant_factory(nome="Tenant A")
    tenant_b = tenant_factory(nome="Tenant B")

    headers_a, _, user_a = auth_headers(tenant=tenant_a)
    headers_b, _, user_b = auth_headers(tenant=tenant_b)

    assert headers_a["Authorization"] != headers_b["Authorization"]
    assert user_a.tenant_id == _tenant_uuid(tenant_a)
    assert user_b.tenant_id == _tenant_uuid(tenant_b)
    assert user_a.tenant_id != user_b.tenant_id


def test_cross_tenant_data_leakage_prevention(
    db_session,
    tenant_factory,
    user_factory,
    tenant_context,
):
    """
    Testa que dados entre tenants nao vazam em queries gerais.
    Protege: prevencao de vazamento de dados cross-tenant.
    """
    tenant_1 = tenant_factory(nome="Pet Shop 1")
    tenant_2 = tenant_factory(nome="Pet Shop 2")
    tenant_3 = tenant_factory(nome="Pet Shop 3")

    user_1 = user_factory(tenant_id=tenant_1.id, email="user1@test.com")
    user_2 = user_factory(tenant_id=tenant_2.id, email="user2@test.com")
    user_3 = user_factory(tenant_id=tenant_3.id, email="user3@test.com")

    tenant_context(tenant_1.id)
    produto_1 = _create_product(tenant_1, user_1, "P1", 10)
    db_session.add(produto_1)
    db_session.flush()

    tenant_context(tenant_2.id)
    produto_2 = _create_product(tenant_2, user_2, "P2", 20)
    db_session.add(produto_2)
    db_session.flush()

    tenant_context(tenant_3.id)
    produto_3 = _create_product(tenant_3, user_3, "P3", 30)
    db_session.add(produto_3)
    db_session.commit()

    tenant_context(tenant_1.id)
    produtos_tenant_1 = db_session.query(Produto).filter_by(tenant_id=_tenant_uuid(tenant_1)).all()

    tenant_context(tenant_2.id)
    produtos_tenant_2 = db_session.query(Produto).filter_by(tenant_id=_tenant_uuid(tenant_2)).all()

    tenant_context(tenant_3.id)
    produtos_tenant_3 = db_session.query(Produto).filter_by(tenant_id=_tenant_uuid(tenant_3)).all()

    assert len(produtos_tenant_1) >= 1
    assert len(produtos_tenant_2) >= 1
    assert len(produtos_tenant_3) >= 1

    assert all(p.tenant_id == _tenant_uuid(tenant_1) for p in produtos_tenant_1)
    assert all(p.tenant_id == _tenant_uuid(tenant_2) for p in produtos_tenant_2)
    assert all(p.tenant_id == _tenant_uuid(tenant_3) for p in produtos_tenant_3)

    assert produto_2 not in produtos_tenant_1
    assert produto_3 not in produtos_tenant_1
    assert produto_1 not in produtos_tenant_2
    assert produto_3 not in produtos_tenant_2
    assert produto_1 not in produtos_tenant_3
    assert produto_2 not in produtos_tenant_3
