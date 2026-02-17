"""
Testes de Idempotência - Handlers de Read Model (Fase 5.3)
============================================================

Valida que handlers são VERDADEIRAMENTE idempotentes:
- Processar o MESMO evento 2x gera o MESMO estado
- Replay não duplica dados
- Sem side effects em modo replay

COBERTURA:
- ✅ Idempotência de VendaCriada
- ✅ Idempotência de VendaFinalizada
- ✅ Idempotência de VendaCancelada
- ✅ Side effects suprimidos em replay
- ✅ Commit responsabilidade do pipeline
"""

import pytest
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Imports do sistema
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.events.base import DomainEvent
from app.domain.events.venda_events import VendaCriada, VendaFinalizada, VendaCancelada
from app.read_models.handlers_v53_idempotente import VendaReadModelHandler
from app.core.side_effects_guard import suppress_in_replay
from app.core.replay_context import enable_replay_mode, disable_replay_mode
from app.core.replay_context import enable_replay_mode, disable_replay_mode


# ===== FIXTURES =====

@pytest.fixture
def test_db():
    """Cria banco em memória para testes"""
    conn = sqlite3.connect(":memory:")
    
    # Criar tabelas
    conn.execute("""
        CREATE TABLE read_vendas_resumo_diario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL UNIQUE,
            quantidade_aberta INTEGER DEFAULT 0,
            quantidade_finalizada INTEGER DEFAULT 0,
            quantidade_cancelada INTEGER DEFAULT 0,
            total_vendido DECIMAL(10, 2) DEFAULT 0,
            total_cancelado DECIMAL(10, 2) DEFAULT 0,
            ticket_medio DECIMAL(10, 2) DEFAULT 0,
            atualizado_em TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE read_performance_parceiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER NOT NULL,
            mes_referencia DATE NOT NULL,
            quantidade_vendas INTEGER DEFAULT 0,
            total_vendido DECIMAL(10, 2) DEFAULT 0,
            vendas_canceladas INTEGER DEFAULT 0,
            taxa_cancelamento DECIMAL(5, 2) DEFAULT 0,
            atualizado_em TIMESTAMP,
            UNIQUE(funcionario_id, mes_referencia)
        )
    """)
    
    conn.execute("""
        CREATE TABLE read_receita_mensal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_referencia DATE NOT NULL UNIQUE,
            receita_bruta DECIMAL(10, 2) DEFAULT 0,
            quantidade_vendas INTEGER DEFAULT 0,
            receita_cancelada DECIMAL(10, 2) DEFAULT 0,
            quantidade_cancelamentos INTEGER DEFAULT 0,
            receita_liquida DECIMAL(10, 2) DEFAULT 0,
            atualizado_em TIMESTAMP
        )
    """)
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db_session(test_db):
    """Mock de Session SQLAlchemy"""
    from sqlalchemy.orm import Session
    from unittest.mock import MagicMock
    
    class MockSession:
        def __init__(self, conn):
            self.conn = conn
        
        def query(self, model):
            return MockQuery(self.conn, model)
        
        def execute(self, stmt):
            # Executar statement SQLAlchemy
            compiled = stmt.compile(dialect=sqlite3.dialect())
            params = compiled.params
            query_str = str(compiled)
            
            cursor = self.conn.execute(query_str, params)
            return cursor
        
        def commit(self):
            self.conn.commit()
        
        def rollback(self):
            self.conn.rollback()
    
    class MockQuery:
        def __init__(self, conn, model):
            self.conn = conn
            self.model = model
            self.filters = []
        
        def filter(self, *args):
            self.filters.extend(args)
            return self
        
        def first(self):
            # Simular busca
            # TODO: implementar busca real se necessário
            return None
    
    return MockSession(test_db)


# ===== TESTES DE IDEMPOTÊNCIA =====

def test_venda_criada_idempotente(mock_db_session):
    """
    CRÍTICO: Processar VendaCriada 2x deve resultar no MESMO estado.
    
    Cenário:
    1. Processar evento VendaCriada
    2. Verificar estado
    3. Processar MESMO evento novamente
    4. Estado deve ser IDÊNTICO
    """
    handler = VendaReadModelHandler(mock_db_session)
    
    evento = VendaCriada(
        venda_id=100,
        numero_venda='202601230001',
        user_id=1,
        cliente_id=42,
        funcionario_id=None,
        total=100.0,
        quantidade_itens=2,
        tem_entrega=False
    )
    
    # 1ª execução
    handler.on_venda_criada(evento)
    mock_db_session.commit()
    
    # Capturar estado após 1ª execução
    cursor = mock_db_session.conn.execute("""
        SELECT quantidade_aberta FROM read_vendas_resumo_diario
        WHERE data = ?
    """, (date.today(),))
    estado_1 = cursor.fetchone()
    
    # 2ª execução (replay)
    handler.on_venda_criada(evento)
    mock_db_session.commit()
    
    # Capturar estado após 2ª execução
    cursor = mock_db_session.conn.execute("""
        SELECT quantidade_aberta FROM read_vendas_resumo_diario
        WHERE data = ?
    """, (date.today(),))
    estado_2 = cursor.fetchone()
    
    # VALIDAÇÃO CRÍTICA
    assert estado_1 == estado_2, \
        f"Handler NÃO é idempotente! Estado 1: {estado_1}, Estado 2: {estado_2}"
    
    print(f"✅ VendaCriada é idempotente: quantidade_aberta={estado_1[0] if estado_1 else None}")


def test_venda_finalizada_idempotente(mock_db_session):
    """
    CRÍTICO: Processar VendaFinalizada 2x = mesmo estado.
    """
    handler = VendaReadModelHandler(mock_db_session)
    
    evento = VendaFinalizada(
        venda_id=200,
        numero_venda='202601230002',
        user_id=1,
        user_nome='Vendedor Teste',
        cliente_id=None,
        funcionario_id=10,
        total=250.0,
        total_pago=250.0,
        status='finalizada',
        formas_pagamento=['PIX'],
        estoque_baixado=True,
        caixa_movimentado=True,
        contas_baixadas=1
    )
    
    # 1ª execução
    handler.on_venda_finalizada(evento)
    mock_db_session.commit()
    
    # Capturar estados
    cursor = mock_db_session.conn.execute("""
        SELECT quantidade_finalizada, total_vendido 
        FROM read_vendas_resumo_diario
        WHERE data = ?
    """, (date.today(),))
    estado_1 = cursor.fetchone()
    
    # 2ª execução (replay)
    handler.on_venda_finalizada(evento)
    mock_db_session.commit()
    
    cursor = mock_db_session.conn.execute("""
        SELECT quantidade_finalizada, total_vendido 
        FROM read_vendas_resumo_diario
        WHERE data = ?
    """, (date.today(),))
    estado_2 = cursor.fetchone()
    
    # VALIDAÇÃO
    assert estado_1 == estado_2, \
        f"VendaFinalizada NÃO é idempotente! Estado 1: {estado_1}, Estado 2: {estado_2}"
    
    print(f"✅ VendaFinalizada idempotente: finalizada={estado_1[0]}, total={estado_1[1]}")


def test_venda_cancelada_idempotente(mock_db_session):
    """
    CRÍTICO: Processar VendaCancelada 2x = mesmo estado.
    """
    handler = VendaReadModelHandler(mock_db_session)
    
    evento = VendaCancelada(
        venda_id=300,
        numero_venda='202601230003',
        user_id=1,
        cliente_id=None,
        funcionario_id=10,
        motivo='Cliente desistiu',
        status_anterior='aberta',
        total=180.0,
        itens_estornados=3,
        contas_canceladas=1,
        comissoes_estornadas=False
    )
    
    # 1ª execução
    handler.on_venda_cancelada(evento)
    mock_db_session.commit()
    
    cursor = mock_db_session.conn.execute("""
        SELECT quantidade_cancelada, total_cancelado 
        FROM read_vendas_resumo_diario
        WHERE data = ?
    """, (date.today(),))
    estado_1 = cursor.fetchone()
    
    # 2ª execução (replay)
    handler.on_venda_cancelada(evento)
    mock_db_session.commit()
    
    cursor = mock_db_session.conn.execute("""
        SELECT quantidade_cancelada, total_cancelado 
        FROM read_vendas_resumo_diario
        WHERE data = ?
    """, (date.today(),))
    estado_2 = cursor.fetchone()
    
    # VALIDAÇÃO
    assert estado_1 == estado_2, \
        f"VendaCancelada NÃO é idempotente! Estado 1: {estado_1}, Estado 2: {estado_2}"
    
    print(f"✅ VendaCancelada idempotente: cancelada={estado_1[0]}, total_cancelado={estado_1[1]}")


def test_side_effects_suprimidos_em_replay():
    """
    Valida que side effects SÃO suprimidos em modo replay.
    """
    # Mock de handler
    class MockHandler:
        side_effect_executed = False
        
        @suppress_in_replay
        def send_notification(self):
            self.side_effect_executed = True
    
    handler = MockHandler()
    
    # Modo normal
    disable_replay_mode()
    handler.send_notification()
    assert handler.side_effect_executed == True, "Side effect deveria executar em modo normal"
    
    # Reset
    handler.side_effect_executed = False
    
    # Modo replay
    enable_replay_mode()
    handler.send_notification()
    assert handler.side_effect_executed == False, "Side effect NÃO deveria executar em modo replay"
    
    # Cleanup
    disable_replay_mode()
    
    print("✅ Side effects corretamente suprimidos em replay")


def test_handler_nao_faz_commit():
    """
    Valida que handlers NÃO fazem commit internamente.
    
    Commit é responsabilidade do pipeline/caller.
    """
    # Este teste é mais conceitual - validamos via inspeção de código
    # que nenhum handler chama self.db.commit()
    
    import inspect
    from app.read_models.handlers_v53_idempotente import VendaReadModelHandler
    
    handler_code = inspect.getsource(VendaReadModelHandler)
    
    # Verificar que não há self.db.commit() nos handlers
    assert "self.db.commit()" not in handler_code, \
        "Handler NÃO deve fazer commit()! Isso é responsabilidade do pipeline."
    
    print("✅ Handlers não fazem commit() (responsabilidade do pipeline)")


# ===== TESTES DE PERFORMANCE =====

def test_upsert_performance(mock_db_session):
    """
    Valida que UPSERT não degrada performance.
    
    Processa 100 eventos do mesmo dia e valida tempo.
    """
    import time
    
    handler = VendaReadModelHandler(mock_db_session)
    
    start = time.time()
    
    for i in range(100):
        evento = VendaCriada(
            venda_id=i,
            numero_venda=f'202601230{i:03d}',
            user_id=1,
            cliente_id=None,
            funcionario_id=None,
            total=100.00,
            quantidade_itens=1,
            tem_entrega=False
        )
        handler.on_venda_criada(evento)
    
    mock_db_session.commit()
    
    elapsed = time.time() - start
    
    print(f"✅ UPSERT performance: 100 eventos em {elapsed:.2f}s ({elapsed/100*1000:.2f}ms/evento)")
    
    # Performance aceitável: < 1s para 100 eventos
    assert elapsed < 1.0, f"Performance degradada: {elapsed:.2f}s para 100 eventos"


# ===== RUNNER =====

if __name__ == "__main__":
    print("=" * 70)
    print("TESTES DE IDEMPOTÊNCIA - HANDLERS READ MODEL (FASE 5.3)")
    print("=" * 70)
    print()
    
    pytest.main([__file__, "-v", "--tb=short"])
