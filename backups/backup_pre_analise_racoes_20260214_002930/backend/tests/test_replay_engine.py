"""
Testes do Replay Engine - Fase 5.4
===================================

Valida:
- Replay total
- Replay parcial (por tenant e por tipo)
- Idempotência (replay 2x = mesmo resultado)
- Rollback em caso de erro
- Ativação/desativação de replay_mode
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.replay import replay_events, ReplayStats
from app.core.replay_context import is_replay_mode, reset_replay_mode
from app.domain.events.event_store import EventStore
from app.domain.events.venda_events import VendaCriada, VendaFinalizada, VendaCancelada
from app.read_models.models import VendasResumoDiario, PerformanceParceiro, ReceitaMensal


@pytest.fixture(autouse=True)
def reset_replay_context():
    """Garante que replay_mode é resetado entre testes"""
    reset_replay_mode()
    yield
    reset_replay_mode()


@pytest.fixture
def db_session():
    """Mock de sessão do banco"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.commit = Mock()
    session.rollback = Mock()
    session.execute = Mock()
    return session


@pytest.fixture
def event_store_with_events(db_session):
    """Event store mockado com eventos de teste"""
    store = EventStore(db_session)
    
    # Mock get_events para retornar eventos de teste
    eventos_mock = [
        {
            'id': '1',
            'sequence_number': 1,
            'event_type': 'VendaCriada',
            'aggregate_id': 'venda-1',
            'aggregate_type': 'venda',
            'user_id': 1,
            'correlation_id': None,
            'causation_id': None,
            'payload': {
                'venda_id': 'venda-1',
                'timestamp': datetime.now().isoformat(),
                'event_id': '1'
            },
            'metadata': {},
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '2',
            'sequence_number': 2,
            'event_type': 'VendaFinalizada',
            'aggregate_id': 'venda-1',
            'aggregate_type': 'venda',
            'user_id': 1,
            'correlation_id': None,
            'causation_id': None,
            'payload': {
                'venda_id': 'venda-1',
                'total': 150.00,
                'funcionario_id': 10,
                'timestamp': datetime.now().isoformat(),
                'event_id': '2'
            },
            'metadata': {},
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '3',
            'sequence_number': 3,
            'event_type': 'VendaCancelada',
            'aggregate_id': 'venda-1',
            'aggregate_type': 'venda',
            'user_id': 1,
            'correlation_id': None,
            'causation_id': None,
            'payload': {
                'venda_id': 'venda-1',
                'motivo': 'Teste',
                'timestamp': datetime.now().isoformat(),
                'event_id': '3'
            },
            'metadata': {},
            'created_at': datetime.now().isoformat()
        }
    ]
    
    store.get_events = Mock(return_value=eventos_mock)
    return store


class TestReplayEngineCore:
    """Testes do motor de replay"""
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_total_processa_todos_eventos(
        self, 
        mock_log_end, 
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay total processa todos os eventos
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            },
            {
                'id': '2',
                'sequence_number': 2,
                'event_type': 'VendaFinalizada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'user_nome': 'Admin',
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'total_pago': 100.0,
                    'status': 'finalizada',
                    'formas_pagamento': ['dinheiro'],
                    'estoque_baixado': True,
                    'caixa_movimentado': True,
                    'contas_baixadas': 1,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '2'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats = replay_events(db_session)
        
        # Assert
        assert stats.success is True
        assert stats.total_events == 2
        assert stats.batches_processed == 1
        assert db_session.commit.called
        assert mock_handler.on_venda_criada.called
        assert mock_handler.on_venda_finalizada.called
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_filtrado_por_user_id(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay filtrado por tenant (user_id)
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 'venda-1',
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats = replay_events(db_session, user_id=1)
        
        # Assert
        mock_store.get_events.assert_called_once()
        call_kwargs = mock_store.get_events.call_args[1]
        assert call_kwargs['user_id'] == 1
        assert stats.filters_applied['user_id'] == 1
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_filtrado_por_tipo_evento(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay filtrado por tipo de evento
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaFinalizada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'user_nome': 'Admin',
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'total_pago': 100.0,
                    'status': 'finalizada',
                    'formas_pagamento': ['dinheiro'],
                    'estoque_baixado': True,
                    'caixa_movimentado': True,
                    'contas_baixadas': 1,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats = replay_events(db_session, event_type='VendaFinalizada')
        
        # Assert
        call_kwargs = mock_store.get_events.call_args[1]
        assert call_kwargs['event_type'] == 'VendaFinalizada'
        assert mock_handler.on_venda_finalizada.called
        assert not mock_handler.on_venda_criada.called


class TestReplayIdempotencia:
    """Testes de idempotência do replay"""
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_duas_vezes_mesmo_resultado(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay 2x deve gerar o mesmo resultado (idempotência)
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats1 = replay_events(db_session)
        stats2 = replay_events(db_session)
        
        # Assert
        assert stats1.total_events == stats2.total_events
        assert stats1.batches_processed == stats2.batches_processed
        assert mock_handler.on_venda_criada.call_count == 2  # Chamado 2x
        assert db_session.commit.call_count >= 4  # 2 replays + 2 auditorias


class TestReplayModeContext:
    """Testes do contexto de replay"""
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_mode_ativo_durante_replay(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: replay_mode deve estar ativo durante o replay
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        replay_mode_during_processing = []
        
        def capture_replay_mode(*args, **kwargs):
            replay_mode_during_processing.append(is_replay_mode())
        
        mock_handler = Mock()
        mock_handler.on_venda_criada.side_effect = capture_replay_mode
        mock_handler_class.return_value = mock_handler
        
        # Act
        assert is_replay_mode() is False  # Antes do replay
        stats = replay_events(db_session)
        
        # Assert
        assert stats.success is True
        assert all(replay_mode_during_processing)  # Estava True durante processamento
        assert is_replay_mode() is False  # Desativado após replay
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_mode_desativado_apos_erro(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: replay_mode deve ser desativado mesmo em caso de erro
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler.on_venda_criada.side_effect = Exception("Erro simulado")
        mock_handler_class.return_value = mock_handler
        
        # Act & Assert
        assert is_replay_mode() is False
        
        with pytest.raises(Exception, match="Erro simulado"):
            replay_events(db_session)
        
        # Replay mode deve estar desativado após erro
        assert is_replay_mode() is False


class TestReplayBatchProcessing:
    """Testes de processamento em batch"""
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_processa_multiplos_batches(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay deve processar múltiplos batches corretamente
        """
        # Arrange - criar 2500 eventos para 3 batches (batch_size=1000)
        eventos = []
        for i in range(2500):
            eventos.append({
                'id': str(i),
                'sequence_number': i,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': i,
                    'numero_venda': f'V{i:04d}',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': str(i)
                }
            })
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats = replay_events(db_session, batch_size=1000)
        
        # Assert
        assert stats.success is True
        assert stats.total_events == 2500
        assert stats.batches_processed == 3  # 1000 + 1000 + 500
        assert db_session.commit.call_count >= 3  # Pelo menos 3 commits (1 por batch)
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_faz_rollback_em_erro_de_batch(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Erro em batch deve causar rollback e abortar replay
        """
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 1,
                    'numero_venda': 'V001',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '1'
                }
            },
            {
                'id': '2',
                'sequence_number': 2,
                'event_type': 'VendaCriada',
                'payload': {
                    'venda_id': 2,
                    'numero_venda': 'V002',
                    'user_id': 1,
                    'cliente_id': 10,
                    'funcionario_id': 5,
                    'total': 100.0,
                    'quantidade_itens': 2,
                    'tem_entrega': False,
                    'timestamp': datetime.now().isoformat(),
                    'event_id': '2'
                }
            }
        ]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        # Handler falha no segundo evento
        mock_handler = Mock()
        mock_handler.on_venda_criada.side_effect = [None, Exception("Erro no evento 2")]
        mock_handler_class.return_value = mock_handler
        
        # Act & Assert
        with pytest.raises(Exception, match="Erro no evento 2"):
            replay_events(db_session, batch_size=2)
        
        # Deve ter feito rollback
        assert db_session.rollback.called
        
        # Auditoria deve registrar falha
        assert mock_log_end.called
        call_args = mock_log_end.call_args[0]
        stats = call_args[1]
        assert stats.success is False
        assert "Erro no evento 2" in stats.error


class TestReplayStats:
    """Testes das estatísticas de replay"""
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_retorna_estatisticas_corretas(
        self,
        mock_log_end,
        mock_log_start,
        mock_handler_class,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay deve retornar estatísticas corretas
        """
        # Arrange
        eventos = [{
            'id': str(i),
            'sequence_number': i,
            'event_type': 'VendaCriada',
            'payload': {
                'venda_id': i,
                'numero_venda': f'V{i:04d}',
                'user_id': 1,
                'cliente_id': 10,
                'funcionario_id': 5,
                'total': 100.0,
                'quantidade_itens': 2,
                'tem_entrega': False,
                'timestamp': datetime.now().isoformat(),
                'event_id': str(i)
            }
        } for i in range(100)]
        
        mock_store = Mock()
        mock_store.get_events.return_value = eventos
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats = replay_events(db_session, user_id=1, event_type='VendaCriada')
        
        # Assert
        assert isinstance(stats, ReplayStats)
        assert stats.total_events == 100
        assert stats.batches_processed == 1
        assert stats.success is True
        assert stats.error is None
        assert stats.filters_applied['user_id'] == 1
        assert stats.filters_applied['event_type'] == 'VendaCriada'
        assert stats.start_time is not None
        assert stats.end_time is not None
        assert stats.duration_seconds >= 0
    
    @patch('app.replay.engine.EventStore')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine._log_replay_end')
    def test_replay_sem_eventos_retorna_stats_vazio(
        self,
        mock_log_end,
        mock_log_start,
        mock_store_class,
        db_session
    ):
        """
        ✅ Teste: Replay sem eventos deve retornar stats zerado
        """
        # Arrange
        mock_store = Mock()
        mock_store.get_events.return_value = []
        mock_store_class.return_value = mock_store
        
        # Act
        stats = replay_events(db_session)
        
        # Assert
        assert stats.total_events == 0
        assert stats.batches_processed == 0
        assert stats.success is True
        assert stats.error is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
