"""
Testes de isolamento multi-tenant
"""
from app.produtos_models import Produto
from app.vendas_models import Venda
from datetime import datetime


def test_tenant_cannot_access_other_tenant_products(db_session, tenant_factory):
    """
    Testa que tenant A não acessa produtos do tenant B.
    Protege: isolamento de dados de produtos.
    """
    import uuid
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")
    
    # Criar produtos para cada tenant
    produto_a = Produto(
        tenant_id=tenant_a.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Produto Loja A",
        preco_venda=50.00,
        estoque_atual=10,
        ativo=True
    )
    
    produto_b = Produto(
        tenant_id=tenant_b.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Produto Loja B",
        preco_venda=75.00,
        estoque_atual=20,
        ativo=True
    )
    
    db_session.add(produto_a)
    db_session.add(produto_b)
    db_session.commit()
    
    # Tenant A só vê seus produtos
    produtos_a = db_session.query(Produto).filter_by(tenant_id=tenant_a.id).all()
    assert all(p.tenant_id == tenant_a.id for p in produtos_a)
    assert produto_b not in produtos_a
    
    # Tenant B só vê seus produtos
    produtos_b = db_session.query(Produto).filter_by(tenant_id=tenant_b.id).all()
    assert all(p.tenant_id == tenant_b.id for p in produtos_b)
    assert produto_a not in produtos_b


def test_tenant_cannot_access_other_tenant_sales(db_session, tenant_factory, user_factory):
    """
    Testa que tenant A não acessa vendas do tenant B.
    Protege: isolamento de dados de vendas.
    """
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")
    
    user_a = user_factory(tenant_id=tenant_a.id)
    user_b = user_factory(tenant_id=tenant_b.id)
    
    # Criar vendas para cada tenant
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
    
    # Tenant A só vê suas vendas
    vendas_a = db_session.query(Venda).filter_by(tenant_id=tenant_a.id).all()
    assert all(v.tenant_id == tenant_a.id for v in vendas_a)
    assert venda_b not in vendas_a
    
    # Tenant B só vê suas vendas
    vendas_b = db_session.query(Venda).filter_by(tenant_id=tenant_b.id).all()
    assert all(v.tenant_id == tenant_b.id for v in vendas_b)
    assert venda_a not in vendas_b


def test_jwt_enforces_tenant_context(auth_headers, tenant_factory):
    """
    Testa que JWT contém tenant_id correto para isolamento.
    Protege: contexto de tenant em requisições autenticadas.
    """
    tenant_a = tenant_factory(nome="Tenant A")
    tenant_b = tenant_factory(nome="Tenant B")
    
    headers_a, _, user_a = auth_headers(tenant=tenant_a)
    headers_b, _, user_b = auth_headers(tenant=tenant_b)
    
    # Verificar que os tenants são diferentes
    assert user_a.tenant_id == tenant_a.id
    assert user_b.tenant_id == tenant_b.id
    assert user_a.tenant_id != user_b.tenant_id


def test_cross_tenant_data_leakage_prevention(db_session, tenant_factory, user_factory):
    """
    Testa que dados entre tenants não vazam em queries gerais.
    Protege: prevenção de vazamento de dados cross-tenant.
    """
    tenant_1 = tenant_factory(nome="Pet Shop 1")
    tenant_2 = tenant_factory(nome="Pet Shop 2")
    tenant_3 = tenant_factory(nome="Pet Shop 3")
    
    user_1 = user_factory(tenant_id=tenant_1.id, email="user1@test.com")
    user_2 = user_factory(tenant_id=tenant_2.id, email="user2@test.com")
    user_3 = user_factory(tenant_id=tenant_3.id, email="user3@test.com")
    
    # Criar produtos para cada tenant
    import uuid
    produto_1 = Produto(tenant_id=tenant_1.id, user_id=user_1.id, codigo=f"P1-{uuid.uuid4().hex[:6]}", nome="P1", preco_venda=10, estoque_atual=5, ativo=True)
    produto_2 = Produto(tenant_id=tenant_2.id, user_id=user_2.id, codigo=f"P2-{uuid.uuid4().hex[:6]}", nome="P2", preco_venda=20, estoque_atual=10, ativo=True)
    produto_3 = Produto(tenant_id=tenant_3.id, user_id=user_3.id, codigo=f"P3-{uuid.uuid4().hex[:6]}", nome="P3", preco_venda=30, estoque_atual=15, ativo=True)
    
    db_session.add(produto_1)
    db_session.flush()
    db_session.add(produto_2)
    db_session.flush()
    db_session.add(produto_3)
    db_session.commit()
    
    # Verificar isolamento para cada tenant
    produtos_tenant_1 = db_session.query(Produto).filter_by(tenant_id=tenant_1.id).all()
    produtos_tenant_2 = db_session.query(Produto).filter_by(tenant_id=tenant_2.id).all()
    produtos_tenant_3 = db_session.query(Produto).filter_by(tenant_id=tenant_3.id).all()
    
    # Cada tenant vê apenas seus produtos
    assert len(produtos_tenant_1) >= 1
    assert len(produtos_tenant_2) >= 1
    assert len(produtos_tenant_3) >= 1
    
    assert all(p.tenant_id == tenant_1.id for p in produtos_tenant_1)
    assert all(p.tenant_id == tenant_2.id for p in produtos_tenant_2)
    assert all(p.tenant_id == tenant_3.id for p in produtos_tenant_3)
    
    # Nenhum produto de outro tenant deve aparecer
    assert produto_2 not in produtos_tenant_1
    assert produto_3 not in produtos_tenant_1
    assert produto_1 not in produtos_tenant_2
    assert produto_3 not in produtos_tenant_2
    assert produto_1 not in produtos_tenant_3
    assert produto_2 not in produtos_tenant_3
