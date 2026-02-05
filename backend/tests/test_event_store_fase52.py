"""
Testes do Event Store - Fase 5.2
=================================

Valida:
- sequence_number monotônico
- Ordenação correta
- Queries de replay
- Integridade de dados
- Rastreabilidade (correlation_id, causation_id)

COBERTURA:
- ✅ Persistência básica
- ✅ Sequence number monotônico
- ✅ Ordenação em queries
- ✅ Filtros de replay
- ✅ Rastreabilidade
- ✅ Integridade da sequência
"""

import pytest
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Imports do sistema
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.events.base import DomainEvent
from app.domain.events.event_store import EventStore


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_db():
    """Cria banco de dados em memória para testes"""
    db_path = ":memory:"
    conn = sqlite3.connect(db_path)
    
    # Criar tabela domain_events (sequence_number é AUTOINCREMENT separado)
    conn.execute("""
        CREATE TABLE domain_events (
            id TEXT PRIMARY KEY NOT NULL,
            sequence_number INTEGER NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            correlation_id TEXT,
            causation_id TEXT,
            payload TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Criar índices
    conn.execute("""
        CREATE INDEX idx_domain_events_sequence 
        ON domain_events (sequence_number)
    """)
    conn.execute("""
        CREATE INDEX idx_domain_events_user_seq 
        ON domain_events (user_id, sequence_number)
    """)
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db_session(test_db):
    """Mock de Session SQLAlchemy"""
    class MockSession:
        def __init__(self, conn):
            self.conn = conn
        
        def execute(self, query, params=None):
            # Converter text() para string
            query_str = str(query)
            
            if params:
                cursor = self.conn.execute(query_str, params)
            else:
                cursor = self.conn.execute(query_str)
            
            # Mock de Result
            class MockResult:
                def __init__(self, cursor):
                    self.cursor = cursor
                
                def fetchone(self):
                    return self.cursor.fetchone()
                
                def fetchall(self):
                    return self.cursor.fetchall()
                
                def __iter__(self):
                    return iter(self.cursor.fetchall())
            
            return MockResult(cursor)
        
        def commit(self):
            self.conn.commit()
        
        def rollback(self):
            self.conn.rollback()
    
    return MockSession(test_db)


# ============================================================================
# EVENTOS DE TESTE
# ============================================================================

@dataclass(frozen=True, kw_only=True)
class VendaCriadaTeste(DomainEvent):
    """Evento de teste para vendas"""
    venda_id: str
    total: float
    user_id: int


@dataclass(frozen=True, kw_only=True)
class PagamentoRecebidoTeste(DomainEvent):
    """Evento de teste para pagamentos"""
    venda_id: str
    valor: float


# ============================================================================
# TESTES DE PERSISTÊNCIA BÁSICA
# ============================================================================

def test_append_evento_simples(mock_db_session):
    """
    Testa persistência básica de evento.
    
    Valida:
    - Evento é salvo no banco
    - sequence_number é gerado automaticamente
    - Dados são preservados corretamente
    """
    store = EventStore(mock_db_session)
    
    evento = VendaCriadaTeste(
        venda_id="venda_123",
        total=150.00,
        user_id=1
    )
    
    # Persistir
    persisted = store.append(
        event=evento,
        user_id=1,
        aggregate_type='venda',
        aggregate_id='venda_123'
    )
    
    # Validar
    assert persisted.sequence_number is not None
    assert persisted.sequence_number > 0
    assert persisted.event_id == evento.event_id
    print(f"✅ Evento persistido com sequence_number={persisted.sequence_number}")


def test_sequence_number_monotonic(mock_db_session):
    """
    Testa que sequence_number SEMPRE cresce (monotonia).
    
    CRÍTICO: Esta é a garantia fundamental para replay determinístico.
    """
    store = EventStore(mock_db_session)
    
    sequence_numbers = []
    
    # Criar 10 eventos
    for i in range(10):
        evento = VendaCriadaTeste(
            venda_id=f"venda_{i}",
            total=100.0 + i,
            user_id=1
        )
        
        persisted = store.append(evento, user_id=1, aggregate_type='venda')
        sequence_numbers.append(persisted.sequence_number)
    
    # Validar monotonia
    for i in range(1, len(sequence_numbers)):
        assert sequence_numbers[i] > sequence_numbers[i-1], \
            f"Sequência quebrada: {sequence_numbers[i-1]} -> {sequence_numbers[i]}"
    
    print(f"✅ Sequence numbers monotônicos: {sequence_numbers}")


def test_sequence_number_sem_gaps(mock_db_session):
    """
    Testa que não há gaps na sequência (1, 2, 3, 4...).
    """
    store = EventStore(mock_db_session)
    
    # Criar 5 eventos
    for i in range(5):
        evento = VendaCriadaTeste(
            venda_id=f"venda_{i}",
            total=100.0,
            user_id=1
        )
        store.append(evento, user_id=1, aggregate_type='venda')
    
    # Validar integridade
    integrity = store.validate_sequence_integrity()
    
    assert integrity['valid'], f"Sequência inválida: {integrity}"
    assert integrity['total_events'] == 5
    print(f"✅ Integridade validada: {integrity}")


# ============================================================================
# TESTES DE ORDENAÇÃO
# ============================================================================

def test_get_events_ordenado_por_sequence(mock_db_session):
    """
    Testa que eventos são retornados em ordem de sequence_number.
    
    CRÍTICO: Replay depende desta ordem.
    """
    store = EventStore(mock_db_session)
    
    # Criar eventos fora de ordem temporal (timestamp diferente)
    eventos = [
        VendaCriadaTeste(venda_id="venda_3", total=300.0, user_id=1),
        VendaCriadaTeste(venda_id="venda_1", total=100.0, user_id=1),
        VendaCriadaTeste(venda_id="venda_2", total=200.0, user_id=1),
    ]
    
    # Persistir
    for evento in eventos:
        store.append(evento, user_id=1, aggregate_type='venda')
    
    # Buscar eventos
    retrieved = store.get_events()
    
    # Validar ordem
    assert len(retrieved) == 3
    
    # Verificar que estão ordenados por sequence_number
    for i in range(1, len(retrieved)):
        assert retrieved[i]['sequence_number'] > retrieved[i-1]['sequence_number']
    
    print(f"✅ Eventos ordenados por sequence_number")
    print(f"   Sequência: {[e['sequence_number'] for e in retrieved]}")


# ============================================================================
# TESTES DE FILTROS (REPLAY)
# ============================================================================

def test_replay_por_user_id(mock_db_session):
    """
    Testa filtro por tenant (user_id).
    
    Caso de uso: Replay de dados de um único cliente.
    """
    store = EventStore(mock_db_session)
    
    # Criar eventos de 2 tenants
    store.append(VendaCriadaTeste(venda_id="v1", total=100, user_id=1), user_id=1, aggregate_type='venda')
    store.append(VendaCriadaTeste(venda_id="v2", total=200, user_id=2), user_id=2, aggregate_type='venda')
    store.append(VendaCriadaTeste(venda_id="v3", total=300, user_id=1), user_id=1, aggregate_type='venda')
    
    # Buscar apenas tenant 1
    events = store.get_events(user_id=1)
    
    assert len(events) == 2
    assert all(e['user_id'] == 1 for e in events)
    print(f"✅ Filtro por user_id funcionando: {len(events)} eventos do tenant 1")


def test_replay_por_event_type(mock_db_session):
    """
    Testa filtro por tipo de evento.
    
    Caso de uso: Reprocessar apenas vendas (não pagamentos).
    """
    store = EventStore(mock_db_session)
    
    # Criar eventos de tipos diferentes
    store.append(VendaCriadaTeste(venda_id="v1", total=100, user_id=1), user_id=1, aggregate_type='venda')
    store.append(PagamentoRecebidoTeste(venda_id="v1", valor=100), user_id=1, aggregate_type='pagamento')
    store.append(VendaCriadaTeste(venda_id="v2", total=200, user_id=1), user_id=1, aggregate_type='venda')
    
    # Buscar apenas VendaCriadaTeste
    events = store.get_events(event_type='VendaCriadaTeste')
    
    assert len(events) == 2
    assert all(e['event_type'] == 'VendaCriadaTeste' for e in events)
    print(f"✅ Filtro por event_type: {len(events)} eventos de venda")


def test_replay_incremental(mock_db_session):
    """
    Testa replay incremental (apenas eventos novos).
    
    Caso de uso: Processar apenas eventos desde último checkpoint.
    """
    store = EventStore(mock_db_session)
    
    # Criar 10 eventos
    for i in range(10):
        store.append(
            VendaCriadaTeste(venda_id=f"v{i}", total=100.0, user_id=1),
            user_id=1,
            aggregate_type='venda'
        )
    
    # Simular checkpoint no evento 5
    last_checkpoint = 5
    
    # Buscar apenas eventos novos
    new_events = store.get_events(from_sequence=last_checkpoint + 1)
    
    assert len(new_events) == 5  # Eventos 6-10
    assert all(e['sequence_number'] > last_checkpoint for e in new_events)
    print(f"✅ Replay incremental: {len(new_events)} novos eventos desde seq={last_checkpoint}")


def test_replay_por_intervalo(mock_db_session):
    """
    Testa replay de intervalo específico.
    
    Caso de uso: Reprocessar eventos de um período.
    """
    store = EventStore(mock_db_session)
    
    # Criar 20 eventos
    for i in range(20):
        store.append(
            VendaCriadaTeste(venda_id=f"v{i}", total=100.0, user_id=1),
            user_id=1,
            aggregate_type='venda'
        )
    
    # Buscar eventos 5-10
    events = store.get_events(from_sequence=5, to_sequence=10)
    
    assert len(events) == 6  # 5, 6, 7, 8, 9, 10
    assert events[0]['sequence_number'] == 5
    assert events[-1]['sequence_number'] == 10
    print(f"✅ Replay por intervalo: {len(events)} eventos entre seq=5 e seq=10")


# ============================================================================
# TESTES DE RASTREABILIDADE
# ============================================================================

def test_correlation_id_rastreia_fluxo(mock_db_session):
    """
    Testa rastreabilidade via correlation_id.
    
    Caso de uso: Rastrear todos eventos de uma venda completa.
    """
    store = EventStore(mock_db_session)
    
    # Criar fluxo: VendaCriada -> PagamentoRecebido
    correlation_id = "flow_venda_123"
    
    evento_venda = VendaCriadaTeste(
        venda_id="v1",
        total=100.0,
        user_id=1,
        correlation_id=correlation_id
    )
    store.append(evento_venda, user_id=1, aggregate_type='venda')
    
    evento_pagamento = PagamentoRecebidoTeste(
        venda_id="v1",
        valor=100.0,
        correlation_id=correlation_id,
        causation_id=evento_venda.event_id
    )
    store.append(evento_pagamento, user_id=1, aggregate_type='pagamento')
    
    # Buscar todos eventos do fluxo
    events = store.get_events()
    flow_events = [e for e in events if e.get('correlation_id') == correlation_id]
    
    assert len(flow_events) == 2
    print(f"✅ Rastreabilidade: {len(flow_events)} eventos no fluxo {correlation_id}")


def test_causation_id_rastreia_causa(mock_db_session):
    """
    Testa rastreabilidade de causa-efeito via causation_id.
    """
    store = EventStore(mock_db_session)
    
    evento_venda = VendaCriadaTeste(venda_id="v1", total=100.0, user_id=1)
    persisted_venda = store.append(evento_venda, user_id=1, aggregate_type='venda')
    
    evento_pagamento = PagamentoRecebidoTeste(
        venda_id="v1",
        valor=100.0,
        causation_id=persisted_venda.event_id
    )
    persisted_pagamento = store.append(evento_pagamento, user_id=1, aggregate_type='pagamento')
    
    # Validar
    events = store.get_events()
    pagamento_event = next(e for e in events if e['event_type'] == 'PagamentoRecebidoTeste')
    
    assert pagamento_event['causation_id'] == persisted_venda.event_id
    print(f"✅ Causation ID rastreado: Pagamento causado por {persisted_venda.event_id}")


# ============================================================================
# TESTES DE INTEGRIDADE
# ============================================================================

def test_validate_sequence_integrity_ok(mock_db_session):
    """
    Testa validação de integridade quando tudo está OK.
    """
    store = EventStore(mock_db_session)
    
    # Criar sequência válida
    for i in range(5):
        store.append(
            VendaCriadaTeste(venda_id=f"v{i}", total=100.0, user_id=1),
            user_id=1,
            aggregate_type='venda'
        )
    
    integrity = store.validate_sequence_integrity()
    
    assert integrity['valid'] is True
    assert integrity['total_events'] == 5
    print(f"✅ Integridade OK: {integrity}")


def test_get_last_sequence_number(mock_db_session):
    """
    Testa obtenção do último sequence_number.
    """
    store = EventStore(mock_db_session)
    
    # Inicialmente vazio
    assert store.get_last_sequence_number() == 0
    
    # Adicionar eventos
    for i in range(3):
        store.append(
            VendaCriadaTeste(venda_id=f"v{i}", total=100.0, user_id=1),
            user_id=1,
            aggregate_type='venda'
        )
    
    last_seq = store.get_last_sequence_number()
    assert last_seq == 3
    print(f"✅ Último sequence_number: {last_seq}")


def test_count_events(mock_db_session):
    """
    Testa contagem de eventos.
    """
    store = EventStore(mock_db_session)
    
    # Criar eventos de 2 tenants
    for i in range(3):
        store.append(VendaCriadaTeste(venda_id=f"v{i}", total=100, user_id=1), user_id=1, aggregate_type='venda')
    
    for i in range(2):
        store.append(VendaCriadaTeste(venda_id=f"v{i+3}", total=100, user_id=2), user_id=2, aggregate_type='venda')
    
    # Contar
    total = store.count_events()
    tenant1 = store.count_events(user_id=1)
    tenant2 = store.count_events(user_id=2)
    
    assert total == 5
    assert tenant1 == 3
    assert tenant2 == 2
    print(f"✅ Contagem: Total={total}, Tenant1={tenant1}, Tenant2={tenant2}")


# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TESTES DO EVENT STORE - FASE 5.2")
    print("=" * 70)
    print()
    
    # Rodar com pytest
    pytest.main([__file__, "-v", "--tb=short"])
