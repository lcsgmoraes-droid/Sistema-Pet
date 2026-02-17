"""
Testes de isolamento multi-tenant
==================================

Valida que:
- Dados de um tenant não vazam para outro
- Mesmo ID pode existir em tenants diferentes
- Queries isolam dados corretamente
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.tenancy.context import set_current_tenant, clear_current_tenant
from app.models import Cliente
from app.produtos_models import Produto


@pytest.fixture(scope='function')
def db_session():
    """
    Cria uma sessão de banco de dados temporária para testes.
    Cada teste roda em uma transação isolada.
    """
    # Engine em memória para testes
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False}
    )
    
    # Criar apenas tabelas específicas para evitar problemas de FK
    Cliente.__table__.create(engine, checkfirst=True)
    Produto.__table__.create(engine, checkfirst=True)
    
    # Criar sessão
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def test_isolamento_mesmo_id_em_tenants_diferentes(db_session):
    """
    Testa que clientes são isolados corretamente entre tenants.
    
    Nota: Em SQLite, IDs são únicos globalmente. Em PostgreSQL com 
    índices tenant-aware, IDs podem repetir entre tenants.
    """
    # Criar cliente no tenant 1
    from uuid import uuid4
    tenant1_id = uuid4()
    tenant2_id = uuid4()
    
    set_current_tenant(tenant1_id)
    c1 = Cliente(
        tenant_id=tenant1_id,
        user_id=1,
        nome='Cliente A - Tenant 1',
        email='clienteA@tenant1.com'
    )
    db_session.add(c1)
    db_session.commit()
    id_c1 = c1.id
    
    # Criar cliente no tenant 2
    set_current_tenant(tenant2_id)
    c2 = Cliente(
        tenant_id=tenant2_id,
        user_id=1,
        nome='Cliente B - Tenant 2',
        email='clienteB@tenant2.com'
    )
    db_session.add(c2)
    db_session.commit()
    id_c2 = c2.id
    
    # Verificar isolamento - Tenant 1 só vê seu cliente
    set_current_tenant(tenant1_id)
    clientes_t1 = db_session.query(Cliente).filter(Cliente.id == id_c1).all()
    assert len(clientes_t1) == 1
    assert clientes_t1[0].nome == 'Cliente A - Tenant 1'
    assert str(clientes_t1[0].tenant_id) == str(tenant1_id)
    
    # Tenant 1 não vê cliente do tenant 2
    cliente_t2_from_t1 = db_session.query(Cliente).filter(Cliente.id == id_c2).first()
    assert cliente_t2_from_t1 is None
    
    # Verificar isolamento - Tenant 2 só vê seu cliente
    set_current_tenant(tenant2_id)
    clientes_t2 = db_session.query(Cliente).filter(Cliente.id == id_c2).all()
    assert len(clientes_t2) == 1
    assert clientes_t2[0].nome == 'Cliente B - Tenant 2'
    assert str(clientes_t2[0].tenant_id) == str(tenant2_id)
    
    # Tenant 2 não vê cliente do tenant 1
    cliente_t1_from_t2 = db_session.query(Cliente).filter(Cliente.id == id_c1).first()
    assert cliente_t1_from_t2 is None
    
    print("✅ Teste: Isolamento completo entre tenants")


def test_acesso_cruzado_bloqueado(db_session):
    """
    Testa que um tenant não consegue acessar dados de outro tenant.
    """
    from uuid import uuid4
    tenant1_id = uuid4()
    tenant2_id = uuid4()
    
    # Criar cliente no tenant 1
    set_current_tenant(tenant1_id)
    c = Cliente(
        id=200,
        tenant_id=tenant1_id,
        user_id=1,
        nome='Cliente Seguro',
        email='seguro@tenant1.com'
    )
    db_session.add(c)
    db_session.commit()
    
    # Tentar acessar do tenant 2
    set_current_tenant(tenant2_id)
    cliente = db_session.query(Cliente).filter(Cliente.id == 200).first()
    
    # Não deve encontrar nada
    assert cliente is None
    
    print("✅ Teste: Acesso cruzado entre tenants bloqueado")


def test_listagem_isolada_por_tenant(db_session):
    """
    Testa que listagens retornam apenas dados do tenant atual.
    """
    from uuid import uuid4
    tenant1_id = uuid4()
    tenant2_id = uuid4()
    
    # Criar 3 clientes no tenant 1
    set_current_tenant(tenant1_id)
    for i in range(1, 4):
        c = Cliente(
            tenant_id=tenant1_id,
            user_id=1,
            nome=f'Cliente T1-{i}',
            email=f'cliente{i}@tenant1.com'
        )
        db_session.add(c)
    db_session.commit()
    
    # Criar 2 clientes no tenant 2
    set_current_tenant(tenant2_id)
    for i in range(1, 3):
        c = Cliente(
            tenant_id=tenant2_id,
            user_id=1,
            nome=f'Cliente T2-{i}',
            email=f'cliente{i}@tenant2.com'
        )
        db_session.add(c)
    db_session.commit()
    
    # Verificar que tenant 1 só vê seus 3 clientes
    set_current_tenant(tenant1_id)
    clientes_t1 = db_session.query(Cliente).all()
    assert len(clientes_t1) == 3
    assert all('T1' in c.nome for c in clientes_t1)
    
    # Verificar que tenant 2 só vê seus 2 clientes
    set_current_tenant(tenant2_id)
    clientes_t2 = db_session.query(Cliente).all()
    assert len(clientes_t2) == 2
    assert all('T2' in c.nome for c in clientes_t2)
    
    print("✅ Teste: Listagens isoladas por tenant")


def test_query_sem_tenant_permite_acesso(db_session):
    """
    Testa que queries sem tenant definido são permitidas
    (para rotas públicas como login).
    """
    from uuid import uuid4
    tenant_id = uuid4()
    
    # Criar cliente
    set_current_tenant(tenant_id)
    c = Cliente(
        tenant_id=tenant_id,
        user_id=1,
        nome='Cliente Teste',
        email='teste@example.com'
    )
    db_session.add(c)
    db_session.commit()
    
    # Limpar tenant (simula rota pública)
    clear_current_tenant()
    
    # Query deve funcionar sem filtro de tenant
    clientes = db_session.query(Cliente).all()
    assert len(clientes) >= 1
    
    print("✅ Teste: Query sem tenant permite acesso (rotas públicas)")


def test_produto_isolado_por_tenant(db_session):
    """
    Testa isolamento de produtos entre tenants.
    """
    from uuid import uuid4
    tenant1_id = uuid4()
    tenant2_id = uuid4()
    
    # Criar produto no tenant 1
    set_current_tenant(tenant1_id)
    p1 = Produto(
        tenant_id=tenant1_id,
        user_id=1,
        codigo='PROD1',
        nome='Ração Premium T1',
        preco_venda=100.00,
        estoque_atual=50
    )
    db_session.add(p1)
    db_session.commit()
    
    # Criar produto no tenant 2
    set_current_tenant(tenant2_id)
    p2 = Produto(
        tenant_id=tenant2_id,
        user_id=1,
        codigo='PROD2',
        nome='Ração Premium T2',
        preco_venda=120.00,
        estoque_atual=30
    )
    db_session.add(p2)
    db_session.commit()
    
    # Verificar isolamento
    set_current_tenant(tenant1_id)
    produtos_t1 = db_session.query(Produto).all()
    assert len(produtos_t1) == 1
    assert produtos_t1[0].preco_venda == 100.00
    
    set_current_tenant(tenant2_id)
    produtos_t2 = db_session.query(Produto).all()
    assert len(produtos_t2) == 1
    assert produtos_t2[0].preco_venda == 120.00
    
    print("✅ Teste: Produtos isolados por tenant")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTES DE ISOLAMENTO MULTI-TENANT")
    print("="*60 + "\n")
    
    pytest.main([__file__, "-v", "-s"])
