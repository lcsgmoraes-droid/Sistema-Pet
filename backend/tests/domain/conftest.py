"""
Configuração de Fixtures para Testes de Domínio
================================================

Mocks e fakes reutilizáveis para todos os testes de domínio.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any


# ============================================================
# FIXTURES DE MOCKS
# ============================================================


@pytest.fixture
def mock_db_session():
    """
    Mock da sessão do SQLAlchemy.
    
    Simula:
    - query()
    - add()
    - commit()
    - rollback()
    - flush()
    - refresh()
    - begin_nested() para savepoints
    """
    session = MagicMock()
    
    # Simular begin_nested (savepoint)
    session.begin_nested.return_value.__enter__ = Mock(return_value=None)
    session.begin_nested.return_value.__exit__ = Mock(return_value=None)
    
    # Simular query builder
    def create_query_mock(model):
        query_mock = MagicMock()
        query_mock.filter_by.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.first.return_value = None
        query_mock.all.return_value = []
        return query_mock
    
    session.query.side_effect = create_query_mock
    
    return session


@pytest.fixture
def mock_estoque_service(monkeypatch):
    """
    Mock do EstoqueService.
    
    Simula:
    - baixar_estoque()
    - estornar_estoque()
    """
    mock = MagicMock()
    
    # Baixar estoque - sucesso
    mock.baixar_estoque.return_value = {
        'produto_nome': 'Ração Premium',
        'estoque_anterior': 100,
        'estoque_novo': 95,
        'quantidade_baixada': 5
    }
    
    # Estornar estoque - sucesso
    mock.estornar_estoque.return_value = {
        'produto_nome': 'Ração Premium',
        'estoque_anterior': 95,
        'estoque_novo': 100,
        'quantidade_estornada': 5
    }
    
    # Monkeypatch no módulo real
    from app.estoque import service as estoque_module
    monkeypatch.setattr(estoque_module, 'EstoqueService', mock)
    
    return mock


@pytest.fixture
def mock_caixa_service(monkeypatch):
    """
    Mock do CaixaService.
    
    Simula:
    - validar_caixa_aberto()
    - registrar_movimentacao_venda()
    - eh_forma_dinheiro()
    """
    mock = MagicMock()
    
    # Caixa aberto
    mock.validar_caixa_aberto.return_value = {
        'caixa_id': 1,
        'saldo_atual': 500.00
    }
    
    # Registrar movimentação
    mock.registrar_movimentacao_venda.return_value = {
        'movimentacao_id': 1,
        'valor': 100.00,
        'saldo_anterior': 500.00,
        'saldo_novo': 600.00
    }
    
    # Forma de pagamento é dinheiro
    mock.eh_forma_dinheiro.side_effect = lambda forma: forma.lower() in ['dinheiro', 'money']
    
    # Monkeypatch no módulo real
    from app.caixa import service as caixa_module
    monkeypatch.setattr(caixa_module, 'CaixaService', mock)
    
    return mock


@pytest.fixture
def mock_contas_receber_service(monkeypatch):
    """
    Mock do ContasReceberService.
    
    Simula:
    - baixar_contas_venda()
    """
    mock = MagicMock()
    
    # Baixar contas
    mock.baixar_contas_venda.return_value = {
        'contas_baixadas': 2,
        'valor_total': 100.00
    }
    
    # Monkeypatch no módulo real (se existir)
    try:
        from app import financeiro
        if hasattr(financeiro, 'ContasReceberService'):
            monkeypatch.setattr(financeiro, 'ContasReceberService', mock)
    except:
        pass
    
    return mock


@pytest.fixture
def mock_event_dispatcher(monkeypatch):
    """
    Mock do EventDispatcher.
    
    Captura eventos publicados sem executar handlers.
    """
    mock = MagicMock()
    
    # Lista para armazenar eventos publicados
    mock.eventos_publicados = []
    
    def publish_side_effect(event):
        mock.eventos_publicados.append(event)
    
    mock.publish.side_effect = publish_side_effect
    
    # Monkeypatch no módulo real
    from app.domain.events import dispatcher as dispatcher_module
    monkeypatch.setattr(dispatcher_module, 'event_dispatcher', mock)
    
    return mock


@pytest.fixture
def fake_venda_data():
    """
    Dados fake para criação de venda.
    """
    return {
        'cliente_id': 1,
        'funcionario_id': None,
        'vendedor_id': None,
        'itens': [
            {
                'produto_id': 10,
                'quantidade': 2,
                'preco_unitario': 50.00,
                'desconto_item': 0,
                'subtotal': 100.00,
                'lote_id': None,
                'pet_id': None
            }
        ],
        'desconto_valor': 0,
        'desconto_percentual': 0,
        'taxa_entrega': 0,
        'tem_entrega': False,
        'observacoes': 'Teste'
    }


@pytest.fixture
def fake_venda_model():
    """
    Mock de uma Venda do modelo.
    """
    venda = MagicMock()
    venda.id = 100
    venda.numero_venda = '202601230001'
    venda.user_id = 1
    venda.cliente_id = 1
    venda.funcionario_id = None
    venda.vendedor_id = None
    venda.status = 'aberta'
    venda.total = Decimal('100.00')
    venda.desconto_valor = Decimal('0')
    venda.taxa_entrega = Decimal('0')
    venda.tem_entrega = False
    venda.observacoes = 'Teste'
    venda.data_venda = datetime.now()
    venda.created_at = datetime.now()
    venda.updated_at = datetime.now()
    venda.data_finalizacao = None
    venda.data_cancelamento = None
    venda.cancelada_por = None
    venda.motivo_cancelamento = None
    
    # Mock do cliente
    venda.cliente = MagicMock()
    venda.cliente.id = 1
    venda.cliente.nome = 'Cliente Teste'
    venda.cliente.credito = Decimal('0')
    
    # Mock do to_dict
    venda.to_dict.return_value = {
        'id': venda.id,
        'numero_venda': venda.numero_venda,
        'status': venda.status,
        'total': float(venda.total),
        'cliente_id': venda.cliente_id,
        'funcionario_id': venda.funcionario_id,
        'tem_entrega': venda.tem_entrega
    }
    
    return venda


@pytest.fixture
def fake_cliente_model():
    """
    Mock de um Cliente do modelo.
    """
    cliente = MagicMock()
    cliente.id = 1
    cliente.nome = 'Cliente Teste'
    cliente.cpf_cnpj = '12345678900'
    cliente.credito = Decimal('50.00')
    cliente.user_id = 1
    return cliente


@pytest.fixture
def fake_pagamentos():
    """
    Dados fake para pagamentos de venda.
    """
    return [
        {
            'forma_pagamento': 'Dinheiro',
            'valor': 100.00,
            'numero_parcelas': 1
        }
    ]


# ============================================================
# FIXTURES DE HELPER
# ============================================================


@pytest.fixture
def assert_evento_publicado():
    """
    Helper para validar que um evento foi publicado.
    """
    def _assert(mock_dispatcher, event_type, **kwargs):
        """
        Valida que um evento do tipo especificado foi publicado.
        
        Args:
            mock_dispatcher: Mock do event dispatcher
            event_type: Classe do evento (ex: VendaCriada)
            **kwargs: Atributos esperados no evento
        """
        eventos = [e for e in mock_dispatcher.eventos_publicados if isinstance(e, event_type)]
        
        assert len(eventos) > 0, f"Nenhum evento {event_type.__name__} foi publicado"
        
        evento = eventos[-1]  # Último evento do tipo
        
        for key, value in kwargs.items():
            assert hasattr(evento, key), f"Evento não tem atributo '{key}'"
            assert getattr(evento, key) == value, (
                f"Evento.{key} = {getattr(evento, key)}, esperado {value}"
            )
        
        return evento
    
    return _assert
