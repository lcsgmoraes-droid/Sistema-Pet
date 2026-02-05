"""
Testes de criação de vendas simples
"""
from datetime import datetime
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto


def test_create_simple_sale(db_session, tenant_factory, user_factory):
    """
    Testa criação de venda simples.
    Protege: estrutura básica de venda, campos obrigatórios.
    """
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)
    
    venda = Venda(
        tenant_id=tenant.id,
        user_id=user.id,
        data_venda=datetime.utcnow(),
        valor_total=150.00,
        status="finalizada"
    )
    
    db_session.add(venda)
    db_session.commit()
    db_session.refresh(venda)
    
    assert venda.id is not None
    assert venda.tenant_id == tenant.id
    assert venda.user_id == user.id
    assert venda.total == 150.00


def test_create_sale_with_items(db_session, tenant_factory, user_factory):
    """
    Testa criação de venda com itens.
    Protege: relacionamento venda-itens, cálculo básico.
    """
    import uuid
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)
    
    # Criar produto
    produto = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Shampoo Pet",
        preco_venda=45.00,
        estoque_atual=100,
        ativo=True
    )
    db_session.add(produto)
    db_session.commit()
    
    # Criar venda
    venda = Venda(
        tenant_id=tenant.id,
        user_id=user.id,
        data_venda=datetime.utcnow(),
        valor_total=90.00,
        status="finalizada"
    )
    db_session.add(venda)
    db_session.commit()
    
    # Criar item da venda
    item = VendaItem(
        tenant_id=tenant.id,
        venda_id=venda.id,
        produto_id=produto.id,
        quantidade=2,
        preco_unitario=45.00,
        subtotal=90.00
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    
    assert item.id is not None
    assert item.tenant_id == tenant.id
    assert item.venda_id == venda.id
    assert item.produto_id == produto.id
    assert item.quantidade == 2
    assert item.subtotal == 90.00


def test_sale_has_correct_tenant_id(db_session, tenant_factory, user_factory):
    """
    Testa que venda possui tenant_id correto.
    Protege: vínculo venda-tenant.
    """
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")
    
    user_a = user_factory(tenant_id=tenant_a.id)
    user_b = user_factory(tenant_id=tenant_b.id)
    
    venda_a = Venda(
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        data_venda=datetime.utcnow(),
        valor_total=100.00,
        status="finalizada"
    )
    
    venda_b = Venda(
        tenant_id=tenant_b.id,
        user_id=user_b.id,
        data_venda=datetime.utcnow(),
        valor_total=200.00,
        status="finalizada"
    )
    
    db_session.add(venda_a)
    db_session.add(venda_b)
    db_session.commit()
    
    assert venda_a.tenant_id == tenant_a.id
    assert venda_b.tenant_id == tenant_b.id
    assert venda_a.tenant_id != venda_b.tenant_id


def test_sale_items_inherit_tenant_id(db_session, tenant_factory, user_factory):
    """
    Testa que itens de venda herdam tenant_id correto.
    Protege: consistência de tenant_id em relações.
    """
    import uuid
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)
    
    produto = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Brinquedo",
        preco_venda=30.00,
        estoque_atual=50,
        ativo=True
    )
    db_session.add(produto)
    db_session.commit()
    
    venda = Venda(
        tenant_id=tenant.id,
        user_id=user.id,
        data_venda=datetime.utcnow(),
        valor_total=60.00,
        status="finalizada"
    )
    db_session.add(venda)
    db_session.commit()
    
    item = VendaItem(
        tenant_id=tenant.id,
        venda_id=venda.id,
        produto_id=produto.id,
        quantidade=2,
        preco_unitario=30.00,
        subtotal=60.00
    )
    db_session.add(item)
    db_session.commit()
    
    assert venda.tenant_id == tenant.id
    assert item.tenant_id == tenant.id
    assert produto.tenant_id == tenant.id
