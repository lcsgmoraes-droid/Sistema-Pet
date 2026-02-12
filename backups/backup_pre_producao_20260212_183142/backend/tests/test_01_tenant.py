"""
Testes de criação e isolamento de Tenants
"""
import uuid
# Import direto para evitar carregar app.__init__.py (que carrega IA/Prophet)
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models import Tenant


def test_create_tenant(db_session, tenant_factory):
    """
    Testa criação básica de tenant.
    Protege: estrutura de tenant, campos obrigatórios.
    """
    tenant = tenant_factory(nome="Pet Shop Central", email="central@petshop.com")
    
    assert tenant.id is not None
    assert tenant.name == "Pet Shop Central"
    assert tenant.email == "central@petshop.com"
    assert tenant.status == "active"
    assert tenant.created_at is not None


def test_tenant_id_is_unique(db_session, tenant_factory):
    """
    Testa que cada tenant possui ID único.
    Protege: unicidade de identificadores.
    """
    tenant1 = tenant_factory(nome="Loja A")
    tenant2 = tenant_factory(nome="Loja B")
    
    assert tenant1.id != tenant2.id


def test_tenant_isolation_by_id(db_session, tenant_factory):
    """
    Testa que dados de diferentes tenants são isolados pelo ID.
    Protege: separação básica de dados por tenant_id.
    """
    tenant_a = tenant_factory(nome="Tenant A")
    tenant_b = tenant_factory(nome="Tenant B")
    
    # Query específica por tenant
    result_a = db_session.query(Tenant).filter_by(id=tenant_a.id).first()
    result_b = db_session.query(Tenant).filter_by(id=tenant_b.id).first()
    
    assert result_a.name == "Tenant A"
    assert result_b.name == "Tenant B"
    assert result_a.id != result_b.id
