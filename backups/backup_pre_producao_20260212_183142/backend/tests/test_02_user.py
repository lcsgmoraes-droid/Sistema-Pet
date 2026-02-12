"""
Testes de criação de usuários e vínculo com tenant
"""
# OTIMIZAÇÃO: Import direto para evitar carregar app.__init__.py (IA/Prophet)
import sys
import os
import hashlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import User


def _hash_password_for_tests(password: str) -> str:
    """Hash simples para testes (SHA256) - mesmo do conftest.py"""
    return hashlib.sha256(password.encode()).hexdigest()


def test_create_user_with_tenant(db_session, tenant_factory, user_factory):
    """
    Testa criação de usuário vinculado a tenant.
    Protege: relacionamento user-tenant, campos obrigatórios.
    """
    tenant = tenant_factory(nome="Loja Teste")
    user = user_factory(
        tenant_id=tenant.id,
        nome="João Silva",
        email="joao@test.com",
        password="senha123"
    )
    
    assert user.id is not None
    assert user.tenant_id == tenant.id
    assert user.nome == "João Silva"
    assert user.email == "joao@test.com"
    assert user.hashed_password is not None


def test_user_password_is_hashed(db_session, tenant_factory, user_factory):
    """
    Testa que senha é armazenada como hash.
    Protege: segurança de armazenamento de credenciais.
    """
    tenant = tenant_factory()
    password_plain = "SenhaForte@123"
    user = user_factory(
        tenant_id=tenant.id,
        password=password_plain
    )
    
    # Senha não deve estar em texto plano
    assert user.hashed_password != password_plain
    
    # Hash deve corresponder (SHA256 para testes)
    expected_hash = _hash_password_for_tests(password_plain)
    assert user.hashed_password == expected_hash


def test_user_belongs_to_correct_tenant(db_session, tenant_factory, user_factory):
    """
    Testa que usuário está vinculado ao tenant correto.
    Protege: integridade do vínculo tenant_id.
    """
    tenant_a = tenant_factory(nome="Loja A")
    tenant_b = tenant_factory(nome="Loja B")
    
    user_a = user_factory(tenant_id=tenant_a.id, email="usera@test.com")
    user_b = user_factory(tenant_id=tenant_b.id, email="userb@test.com")
    
    assert user_a.tenant_id == tenant_a.id
    assert user_b.tenant_id == tenant_b.id
    assert user_a.tenant_id != user_b.tenant_id


def test_multiple_users_same_tenant(db_session, tenant_factory, user_factory):
    """
    Testa que múltiplos usuários podem pertencer ao mesmo tenant.
    Protege: cardinalidade 1:N tenant-users.
    """
    tenant = tenant_factory(nome="Pet Shop XYZ")
    
    user1 = user_factory(tenant_id=tenant.id, email="user1@test.com")
    user2 = user_factory(tenant_id=tenant.id, email="user2@test.com")
    user3 = user_factory(tenant_id=tenant.id, email="user3@test.com")
    
    users = db_session.query(User).filter_by(tenant_id=tenant.id).all()
    
    assert len(users) >= 3
    assert all(u.tenant_id == tenant.id for u in users)
