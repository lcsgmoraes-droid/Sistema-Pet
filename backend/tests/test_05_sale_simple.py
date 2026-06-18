"""
Testes de criacao de vendas simples.
"""

from datetime import datetime
from uuid import UUID, uuid4

from app.produtos_models import Produto
from app.vendas_models import Venda, VendaItem


def _tenant_uuid(tenant):
    return UUID(str(tenant.id))


def _sale_number() -> str:
    return f"TST-{uuid4().hex[:8].upper()}"


def _create_sale(tenant, user, total: float) -> Venda:
    return Venda(
        tenant_id=_tenant_uuid(tenant),
        user_id=user.id,
        vendedor_id=user.id,
        numero_venda=_sale_number(),
        data_venda=datetime.utcnow(),
        subtotal=total,
        total=total,
        status="finalizada",
    )


def _create_product(tenant, user, nome: str, preco: float) -> Produto:
    return Produto(
        tenant_id=_tenant_uuid(tenant),
        user_id=user.id,
        codigo=f"PROD-{uuid4().hex[:8].upper()}",
        nome=nome,
        preco_venda=preco,
        estoque_atual=100,
        ativo=True,
    )


def test_create_simple_sale(db_session, tenant_factory, user_factory):
    """
    Testa criacao de venda simples.
    Protege: estrutura basica de venda, campos obrigatorios.
    """
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)

    venda = _create_sale(tenant, user, total=150.00)

    db_session.add(venda)
    db_session.commit()
    db_session.refresh(venda)

    assert venda.id is not None
    assert venda.tenant_id == _tenant_uuid(tenant)
    assert venda.user_id == user.id
    assert venda.vendedor_id == user.id
    assert float(venda.total) == 150.00


def test_create_sale_with_items(db_session, tenant_factory, user_factory):
    """
    Testa criacao de venda com itens.
    Protege: relacionamento venda-itens, calculo basico.
    """
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)

    produto = _create_product(tenant, user, "Shampoo Pet", 45.00)
    db_session.add(produto)
    db_session.commit()

    venda = _create_sale(tenant, user, total=90.00)
    db_session.add(venda)
    db_session.commit()

    item = VendaItem(
        tenant_id=_tenant_uuid(tenant),
        venda_id=venda.id,
        tipo="produto",
        produto_id=produto.id,
        quantidade=2,
        preco_unitario=45.00,
        subtotal=90.00,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert item.tenant_id == _tenant_uuid(tenant)
    assert item.venda_id == venda.id
    assert item.produto_id == produto.id
    assert float(item.quantidade) == 2
    assert float(item.subtotal) == 90.00


def test_sale_has_correct_tenant_id(
    db_session, tenant_factory, user_factory, tenant_context
):
    """
    Testa que venda possui tenant_id correto.
    Protege: vinculo venda-tenant.
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

    assert venda_a.tenant_id == _tenant_uuid(tenant_a)
    assert venda_b.tenant_id == _tenant_uuid(tenant_b)
    assert venda_a.tenant_id != venda_b.tenant_id


def test_sale_items_inherit_tenant_id(db_session, tenant_factory, user_factory):
    """
    Testa que itens de venda herdam tenant_id correto.
    Protege: consistencia de tenant_id em relacoes.
    """
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)

    produto = _create_product(tenant, user, "Brinquedo", 30.00)
    db_session.add(produto)
    db_session.commit()

    venda = _create_sale(tenant, user, total=60.00)
    db_session.add(venda)
    db_session.commit()

    item = VendaItem(
        tenant_id=_tenant_uuid(tenant),
        venda_id=venda.id,
        tipo="produto",
        produto_id=produto.id,
        quantidade=2,
        preco_unitario=30.00,
        subtotal=60.00,
    )
    db_session.add(item)
    db_session.commit()

    assert venda.tenant_id == _tenant_uuid(tenant)
    assert item.tenant_id == _tenant_uuid(tenant)
    assert produto.tenant_id == _tenant_uuid(tenant)
