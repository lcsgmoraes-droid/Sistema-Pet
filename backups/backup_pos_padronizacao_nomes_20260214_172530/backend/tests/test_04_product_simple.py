"""
Testes de criação de produtos simples
"""
# OTIMIZAÇÃO: Import direto para evitar carregar app.__init__.py (IA/Prophet)
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.produtos_models import Produto


def test_create_simple_product(db_session, tenant_factory, user_factory):
    """
    Testa criação de produto simples.
    Protege: estrutura básica de produto, campos obrigatórios.
    """
    import uuid
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)
    
    produto = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Ração Premium 15kg",
        preco_venda=120.00,
        estoque_atual=50,
        ativo=True
    )
    
    db_session.add(produto)
    db_session.commit()
    db_session.refresh(produto)
    
    assert produto.id is not None
    assert produto.tenant_id == tenant.id
    assert produto.nome == "Ração Premium 15kg"
    assert produto.preco_venda == 120.00
    assert produto.estoque_atual == 50


def test_product_persistence(db_session, tenant_factory, user_factory):
    """
    Testa que produto persiste corretamente no banco.
    Protege: integridade de dados após commit.
    """
    import uuid
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)
    
    produto = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Coleira Ajustável",
        preco_venda=35.50,
        estoque_atual=100,
        ativo=True
    )
    
    db_session.add(produto)
    db_session.commit()
    produto_id = produto.id
    
    # Consultar novamente
    produto_retrieved = db_session.query(Produto).filter_by(id=produto_id).first()
    
    assert produto_retrieved is not None
    assert produto_retrieved.nome == "Coleira Ajustável"
    assert produto_retrieved.tenant_id == tenant.id


def test_product_has_correct_tenant_id(db_session, tenant_factory, user_factory):
    """
    Testa que produto possui tenant_id correto.
    Protege: vínculo produto-tenant.
    """
    import uuid
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")
    user_a = user_factory(tenant_id=tenant_a.id)
    user_b = user_factory(tenant_id=tenant_b.id)
    
    produto_a = Produto(
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Produto A",
        preco_venda=10.00,
        estoque_atual=5,
        ativo=True
    )
    db_session.add(produto_a)
    db_session.commit()
    
    produto_b = Produto(
        tenant_id=tenant_b.id,
        user_id=user_b.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Produto B",
        preco_venda=20.00,
        estoque_atual=10,
        ativo=True
    )
    db_session.add(produto_b)
    db_session.commit()
    
    assert produto_a.tenant_id == tenant_a.id
    assert produto_b.tenant_id == tenant_b.id
    assert produto_a.tenant_id != produto_b.tenant_id


def test_query_products_by_tenant(db_session, tenant_factory, user_factory):
    """
    Testa consulta de produtos filtrados por tenant.
    Protege: isolamento de produtos por tenant.
    """
    import uuid
    tenant = tenant_factory()
    user = user_factory(tenant_id=tenant.id)
    
    produto1 = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Produto 1",
        preco_venda=15.00,
        estoque_atual=10,
        ativo=True
    )
    db_session.add(produto1)
    db_session.commit()
    
    produto2 = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo=f"PROD-{uuid.uuid4().hex[:8].upper()}",
        nome="Produto 2",
        preco_venda=25.00,
        estoque_atual=20,
        ativo=True
    )
    db_session.add(produto2)
    db_session.commit()
    
    produtos = db_session.query(Produto).filter_by(tenant_id=tenant.id).all()
    
    assert len(produtos) >= 2
    assert all(p.tenant_id == tenant.id for p in produtos)
