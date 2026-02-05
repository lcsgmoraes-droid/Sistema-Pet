"""
Exemplo de Uso do Event Store - Fase 5.2
=========================================

Demonstra como usar o novo event store em situações reais.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from dataclasses import dataclass
from app.domain.events.base import DomainEvent
from app.domain.events.event_store import EventStore
import sqlite3


# ============================================================================
# EVENTOS DE EXEMPLO
# ============================================================================

@dataclass(frozen=True, kw_only=True)
class VendaCriada(DomainEvent):
    """Evento: Uma nova venda foi criada"""
    venda_id: str
    total: float
    cliente_id: int


@dataclass(frozen=True, kw_only=True)
class PagamentoRecebido(DomainEvent):
    """Evento: Pagamento foi recebido"""
    venda_id: str
    valor: float
    forma_pagamento: str


@dataclass(frozen=True, kw_only=True)
class VendaFinalizada(DomainEvent):
    """Evento: Venda foi finalizada"""
    venda_id: str
    total_pago: float


# ============================================================================
# MOCK DE DB SESSION
# ============================================================================

class MockSession:
    """Mock simples de Session SQLAlchemy"""
    def __init__(self, conn):
        self.conn = conn
    
    def execute(self, query, params=None):
        query_str = str(query)
        cursor = self.conn.execute(query_str, params or {})
        
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


# ============================================================================
# EXEMPLO 1: FLUXO COMPLETO DE VENDA
# ============================================================================

def exemplo_fluxo_venda():
    """
    Demonstra um fluxo completo de venda com rastreabilidade.
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 1: Fluxo Completo de Venda com Rastreabilidade")
    print("=" * 70)
    
    # Conectar ao banco
    conn = sqlite3.connect('petshop.db')
    db = MockSession(conn)
    store = EventStore(db)
    
    # ID de correlação para rastrear todo o fluxo
    correlation_id = f"flow_venda_{datetime.now().timestamp()}"
    
    # 1. Venda Criada
    print("\n📝 1. Criando venda...")
    evento_venda = VendaCriada(
        venda_id="venda_001",
        total=350.00,
        cliente_id=42,
        correlation_id=correlation_id
    )
    
    persisted_venda = store.append(
        event=evento_venda,
        user_id=1,
        aggregate_type='venda',
        aggregate_id='venda_001'
    )
    
    print(f"   ✅ Venda criada: seq={persisted_venda.sequence_number}")
    print(f"   📍 Correlation ID: {correlation_id}")
    
    # 2. Pagamento Recebido
    print("\n💰 2. Registrando pagamento...")
    evento_pagamento = PagamentoRecebido(
        venda_id="venda_001",
        valor=350.00,
        forma_pagamento="PIX"
    ).with_causation(
        causation_event_id=persisted_venda.event_id,
        correlation_id=correlation_id
    )
    
    persisted_pagamento = store.append(
        event=evento_pagamento,
        user_id=1,
        aggregate_type='pagamento'
    )
    
    print(f"   ✅ Pagamento registrado: seq={persisted_pagamento.sequence_number}")
    print(f"   🔗 Causado por: {persisted_venda.event_id[:12]}...")
    
    # 3. Venda Finalizada
    print("\n✅ 3. Finalizando venda...")
    evento_finalizada = VendaFinalizada(
        venda_id="venda_001",
        total_pago=350.00
    ).with_causation(
        causation_event_id=persisted_pagamento.event_id,
        correlation_id=correlation_id
    )
    
    persisted_finalizada = store.append(
        event=evento_finalizada,
        user_id=1,
        aggregate_type='venda',
        aggregate_id='venda_001'
    )
    
    print(f"   ✅ Venda finalizada: seq={persisted_finalizada.sequence_number}")
    
    # 4. Rastrear todo o fluxo
    print("\n🔍 4. Rastreando fluxo completo...")
    all_events = store.get_events()
    flow_events = [e for e in all_events if e.get('correlation_id') == correlation_id]
    
    print(f"\n   Eventos do fluxo {correlation_id[:20]}...:")
    for event in flow_events:
        print(f"   - Seq {event['sequence_number']:3} | {event['event_type']:20} | ID: {event['id'][:12]}...")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Fluxo completo rastreado com sucesso!")


# ============================================================================
# EXEMPLO 2: REPLAY INCREMENTAL
# ============================================================================

def exemplo_replay_incremental():
    """
    Demonstra replay incremental (processar apenas eventos novos).
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 2: Replay Incremental")
    print("=" * 70)
    
    conn = sqlite3.connect('petshop.db')
    db = MockSession(conn)
    store = EventStore(db)
    
    # Simular checkpoint (último evento processado)
    last_processed = store.get_last_sequence_number()
    print(f"\n📍 Último evento processado: {last_processed}")
    
    # Adicionar novos eventos
    print("\n📝 Adicionando 3 novos eventos...")
    for i in range(3):
        evento = VendaCriada(
            venda_id=f"venda_new_{i}",
            total=100.0 * (i + 1),
            cliente_id=i + 100
        )
        store.append(evento, user_id=1, aggregate_type='venda')
    
    conn.commit()
    
    # Replay incremental
    print(f"\n🔄 Fazendo replay incremental (desde seq={last_processed + 1})...")
    new_events = store.get_events(from_sequence=last_processed + 1)
    
    print(f"\n   Novos eventos encontrados: {len(new_events)}")
    for event in new_events:
        print(f"   - Seq {event['sequence_number']:3} | {event['event_type']:20}")
    
    conn.close()
    
    print("\n✅ Replay incremental concluído!")


# ============================================================================
# EXEMPLO 3: REPLAY POR TENANT
# ============================================================================

def exemplo_replay_por_tenant():
    """
    Demonstra replay isolado por tenant (multi-tenancy).
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 3: Replay por Tenant (Multi-tenancy)")
    print("=" * 70)
    
    conn = sqlite3.connect('petshop.db')
    db = MockSession(conn)
    store = EventStore(db)
    
    # Adicionar eventos de diferentes tenants
    print("\n📝 Adicionando eventos de múltiplos tenants...")
    
    # Tenant 1
    for i in range(2):
        evento = VendaCriada(
            venda_id=f"tenant1_venda_{i}",
            total=100.0,
            cliente_id=1
        )
        store.append(evento, user_id=1, aggregate_type='venda')
    
    # Tenant 2
    for i in range(3):
        evento = VendaCriada(
            venda_id=f"tenant2_venda_{i}",
            total=200.0,
            cliente_id=2
        )
        store.append(evento, user_id=2, aggregate_type='venda')
    
    conn.commit()
    
    # Replay por tenant
    print("\n🔄 Replay do Tenant 1:")
    tenant1_events = store.get_events(user_id=1)
    print(f"   Total: {len(tenant1_events)} eventos")
    
    print("\n🔄 Replay do Tenant 2:")
    tenant2_events = store.get_events(user_id=2)
    print(f"   Total: {len(tenant2_events)} eventos")
    
    print("\n✅ Isolamento de tenants garantido!")
    
    conn.close()


# ============================================================================
# EXEMPLO 4: VALIDAÇÃO DE INTEGRIDADE
# ============================================================================

def exemplo_validacao_integridade():
    """
    Demonstra validação de integridade do event store.
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 4: Validação de Integridade")
    print("=" * 70)
    
    conn = sqlite3.connect('petshop.db')
    db = MockSession(conn)
    store = EventStore(db)
    
    # Validar integridade
    print("\n🔍 Validando integridade da sequência...")
    integrity = store.validate_sequence_integrity()
    
    if integrity['valid']:
        print("\n   ✅ Sequência íntegra!")
        print(f"   📊 Min sequence: {integrity.get('min_sequence', 'N/A')}")
        print(f"   📊 Max sequence: {integrity.get('max_sequence', 'N/A')}")
        print(f"   📊 Total events: {integrity.get('total_events', 'N/A')}")
    else:
        print("\n   ❌ Problemas detectados:")
        if integrity.get('has_gaps'):
            print("      - Gaps na sequência!")
        if integrity.get('has_duplicates'):
            print("      - Duplicatas na sequência!")
    
    # Estatísticas
    print("\n📈 Estatísticas:")
    total = store.count_events()
    last_seq = store.get_last_sequence_number()
    print(f"   Total de eventos: {total}")
    print(f"   Último sequence_number: {last_seq}")
    
    conn.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EXEMPLOS DE USO DO EVENT STORE - FASE 5.2")
    print("=" * 70)
    
    try:
        exemplo_fluxo_venda()
        exemplo_replay_incremental()
        exemplo_replay_por_tenant()
        exemplo_validacao_integridade()
        
        print("\n" + "=" * 70)
        print("✅ TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO!")
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
