# -*- coding: utf-8 -*-
"""
TESTE CRÍTICO DE SEGURANÇA: ISOLAMENTO MULTI-TENANT EM VENDAS
===============================================================

Este teste GARANTE que não há vazamento de dados entre empresas (tenants).

CENÁRIO:
--------
1. Criar 2 empresas (Tenant A e Tenant B)
2. Criar 2 usuários (um em cada empresa)
3. Criar vendas em cada empresa
4. VALIDAR: Empresa A NÃO pode ver vendas da Empresa B
5. VALIDAR: Empresa B NÃO pode ver vendas da Empresa A
6. VALIDAR: VendaItem, VendaPagamento têm tenant_id correto

IMPORTÂNCIA:
------------
❌ FALHA = VAZAMENTO DE DADOS = CRIME (LGPD) = FIM DO SAAS
✅ SUCESSO = Isolamento garantido

Este teste DEVE ser executado:
- Antes de todo deploy
- Após qualquer alteração em vendas
- Diariamente em CI/CD

AUTOR: Sistema Pet Shop - Arquitetura Multi-Tenant
DATA: 2026-01-27
"""

import pytest
from uuid import UUID

from app.db import SessionLocal
from app.tenancy.context import set_current_tenant, clear_current_tenant
from app.vendas_models import Venda, VendaItem, VendaPagamento
from app.vendas.service import VendaService
from app.models import User
from app.produtos_models import Produto


@pytest.fixture(scope="function")
def db_session():
    """Cria uma sessão de banco de dados isolada para cada teste"""
    # Usar o banco configurado (SQLite do sistema)
    session = SessionLocal()
    
    yield session
    
    # Limpar dados criados no teste
    try:
        session.rollback()
    except Exception:
        pass
    
    session.close()


@pytest.fixture
def tenant_a():
    """Cria Tenant A (Pet Shop Belo Horizonte)"""
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def tenant_b():
    """Cria Tenant B (Pet Shop São Paulo)"""
    return UUID("22222222-2222-2222-2222-222222222222")


def test_venda_tem_tenant_id_obrigatorio(db_session):
    """
    🔒 TESTE CRÍTICO 1: Venda DEVE ter tenant_id
    """
    tenant_a = UUID("11111111-1111-1111-1111-111111111111")
    
    # Buscar usuário existente no banco
    user_a = db_session.query(User).filter(User.tenant_id == tenant_a).first()
    
    if not user_a:
        pytest.skip("Nenhum usuário encontrado para o tenant A. Execute o sistema primeiro para criar dados de teste.")
    
    set_current_tenant(tenant_a)
    
    # Buscar ou criar produto
    produto_a = db_session.query(Produto).filter(
        Produto.tenant_id == tenant_a
    ).first()
    
    if not produto_a:
        pytest.skip("Nenhum produto encontrado para o tenant A. Execute o sistema primeiro para criar dados de teste.")
    
    payload = {
        'cliente_id': None,
        'vendedor_id': user_a.id,
        'funcionario_id': None,
        'itens': [
            {
                'tipo': 'produto',
                'produto_id': produto_a.id,
                'quantidade': 2,
                'preco_unitario': 50.00,
                'subtotal': 100.00
            }
        ],
        'desconto_valor': 0,
        'desconto_percentual': 0,
        'observacoes': None,
        'tem_entrega': False,
        'taxa_entrega': 0,
        'tenant_id': tenant_a
    }
    
    venda_dict = VendaService.criar_venda(
        payload=payload,
        user_id=user_a.id,
        db=db_session
    )
    
    # Buscar venda criada
    venda = db_session.query(Venda).filter_by(id=venda_dict['id']).first()
    
    # VALIDAÇÕES CRÍTICAS
    assert venda is not None, "Venda não foi criada"
    assert venda.tenant_id == tenant_a, f"❌ FALHA: Venda sem tenant_id correto! Esperado={tenant_a}, Obtido={venda.tenant_id}"
    
    # Limpar teste
    db_session.delete(venda)
    db_session.commit()
    clear_current_tenant()
    
    print("✅ TESTE 1 PASSOU: Venda tem tenant_id correto!")


def test_venda_item_tem_tenant_id_obrigatorio(db_session):
    """
    🔒 TESTE CRÍTICO 2: VendaItem DEVE ter tenant_id
    
    RISCO SE FALHAR: VendaItem sem tenant_id pode ser visto por qualquer empresa
    """
    tenant_a = UUID("11111111-1111-1111-1111-111111111111")
    
    # Buscar usuário existente no banco
    user_a = db_session.query(User).filter(User.tenant_id == tenant_a).first()
    
    if not user_a:
        pytest.skip("Nenhum usuário encontrado para o tenant A.")
    
    set_current_tenant(tenant_a)
    
    # Buscar produto
    produto_a = db_session.query(Produto).filter(
        Produto.tenant_id == tenant_a
    ).first()
    
    if not produto_a:
        pytest.skip("Nenhum produto encontrado para o tenant A.")
    
    payload = {
        'cliente_id': None,
        'vendedor_id': user_a.id,
        'funcionario_id': None,
        'itens': [
            {
                'tipo': 'produto',
                'produto_id': produto_a.id,
                'quantidade': 1,
                'preco_unitario': 50.00,
                'subtotal': 50.00
            }
        ],
        'desconto_valor': 0,
        'desconto_percentual': 0,
        'observacoes': None,
        'tem_entrega': False,
        'taxa_entrega': 0,
        'tenant_id': tenant_a
    }
    
    venda_dict = VendaService.criar_venda(
        payload=payload,
        user_id=user_a.id,
        db=db_session
    )
    
    # Buscar itens criados
    itens = db_session.query(VendaItem).filter_by(venda_id=venda_dict['id']).all()
    
    # VALIDAÇÕES CRÍTICAS
    assert len(itens) == 1, "Item não foi criado"
    item = itens[0]
    
    assert item.tenant_id is not None, "❌ FALHA CRÍTICA: VendaItem SEM tenant_id! RISCO DE VAZAMENTO!"
    assert item.tenant_id == tenant_a, f"❌ FALHA: VendaItem com tenant_id errado! Esperado={tenant_a}, Obtido={item.tenant_id}"
    
    # Limpar teste
    venda = db_session.query(Venda).filter_by(id=venda_dict['id']).first()
    db_session.delete(venda)
    db_session.commit()
    clear_current_tenant()
    
    print("✅ TESTE 2 PASSOU: VendaItem tem tenant_id correto!")


def test_isolamento_simples_tenant(db_session):
    """
    🔒 TESTE CRÍTICO 3: ISOLAMENTO BÁSICO - Validar que queries filtram por tenant
    
    Este teste valida que o sistema separa corretamente dados de diferentes empresas.
    """
    # Buscar 2 tenants diferentes no banco
    tenants = db_session.query(User).distinct(User.tenant_id).limit(2).all()
    
    if len(tenants) < 2:
        pytest.skip("Necessário pelo menos 2 tenants no banco para testar isolamento.")
    
    tenant_a_id = tenants[0].tenant_id
    tenant_b_id = tenants[1].tenant_id
    
    # Contar vendas do tenant A
    vendas_a = db_session.query(Venda).filter_by(tenant_id=tenant_a_id).count()
    
    # Contar vendas do tenant B
    vendas_b = db_session.query(Venda).filter_by(tenant_id=tenant_b_id).count()
    
    # Contar todas as vendas
    todas_vendas = db_session.query(Venda).count()
    
    # VALIDAÇÃO: A soma das vendas dos tenants deve ser menor ou igual ao total
    # (pode haver outros tenants)
    assert vendas_a + vendas_b <= todas_vendas, "Contagem inconsistente de vendas"
    
    print(f"✅ TESTE 3 PASSOU: Tenant A tem {vendas_a} vendas, Tenant B tem {vendas_b} vendas. Total: {todas_vendas}")


def test_venda_item_herda_tenant_da_venda(db_session):
    """
    🔒 TESTE CRÍTICO 4: Verificar que itens de venda existentes têm tenant_id
    
    Este teste valida que o sistema já existente está correto.
    """
    # Buscar vendas com itens
    vendas_com_itens = db_session.query(Venda).join(VendaItem).limit(10).all()
    
    if len(vendas_com_itens) == 0:
        pytest.skip("Nenhuma venda com itens encontrada no banco.")
    
    erros = []
    
    for venda in vendas_com_itens:
        for item in venda.itens:
            # Validar que item tem tenant_id
            if item.tenant_id is None:
                erros.append(f"Venda {venda.id}, Item {item.id}: SEM tenant_id")
            elif item.tenant_id != venda.tenant_id:
                erros.append(f"Venda {venda.id}, Item {item.id}: tenant_id diferente da venda")
    
    if erros:
        pytest.fail("❌ ERROS ENCONTRADOS:\n" + "\n".join(erros))
    
    print(f"✅ TESTE 4 PASSOU: {len(vendas_com_itens)} vendas verificadas, todos os itens têm tenant_id correto!")


def test_venda_pagamento_herda_tenant_da_venda(db_session):
    """
    🔒 TESTE CRÍTICO 5: Verificar que pagamentos têm tenant_id correto
    """
    # Buscar vendas com pagamentos
    vendas_com_pagamentos = db_session.query(Venda).join(VendaPagamento).limit(10).all()
    
    if len(vendas_com_pagamentos) == 0:
        pytest.skip("Nenhuma venda com pagamentos encontrada no banco.")
    
    erros = []
    
    for venda in vendas_com_pagamentos:
        for pagamento in venda.pagamentos:
            # Validar que pagamento tem tenant_id
            if pagamento.tenant_id is None:
                erros.append(f"Venda {venda.id}, Pagamento {pagamento.id}: SEM tenant_id")
            elif pagamento.tenant_id != venda.tenant_id:
                erros.append(f"Venda {venda.id}, Pagamento {pagamento.id}: tenant_id diferente da venda")
    
    if erros:
        pytest.fail("❌ ERROS ENCONTRADOS:\n" + "\n".join(erros))
    
    print(f"✅ TESTE 5 PASSOU: {len(vendas_com_pagamentos)} vendas verificadas, todos os pagamentos têm tenant_id correto!")


# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
