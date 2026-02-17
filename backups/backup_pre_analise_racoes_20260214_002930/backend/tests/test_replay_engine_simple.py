"""
Testes Simplificados do Replay Engine - Fase 5.4
==================================================

Testa as funcionalidades essenciais do motor de replay.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.replay import replay_events, ReplayStats
from app.core.replay_context import is_replay_mode, reset_replay_mode


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
    session.commit = Mock()
    session.rollback = Mock()
    session.execute = Mock()
    return session


def create_venda_criada_payload(venda_id=1):
    """Helper para criar payload completo de VendaCriada"""
    return {
        'venda_id': venda_id,
        'numero_venda': f'V{venda_id:04d}',
        'user_id': 1,
        'cliente_id': 10,
        'funcionario_id': 5,
        'total': 100.0,
        'quantidade_itens': 2,
        'tem_entrega': False,
        'timestamp': datetime.now().isoformat(),
        'event_id': str(venda_id)
    }


def create_venda_finalizada_payload(venda_id=1):
    """Helper para criar payload completo de VendaFinalizada"""
    return {
        'venda_id': venda_id,
        'numero_venda': f'V{venda_id:04d}',
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
        'event_id': str(venda_id)
    }


class TestReplayEngineCore:
    """Testes básicos do motor de replay"""
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_total_processa_eventos(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: Replay deve processar eventos com sucesso"""
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': create_venda_criada_payload(1)
            },
            {
                'id': '2',
                'sequence_number': 2,
                'event_type': 'VendaFinalizada',
                'payload': create_venda_finalizada_payload(1)
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
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_aplica_filtros_corretamente(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: Replay deve aplicar filtros ao buscar eventos"""
        # Arrange
        mock_store = Mock()
        mock_store.get_events.return_value = []
        mock_store_class.return_value = mock_store
        
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        
        # Act
        stats = replay_events(
            db_session,
            user_id=1,
            event_type='VendaFinalizada',
            from_sequence=100
        )
        
        # Assert
        mock_store.get_events.assert_called_once()
        call_kwargs = mock_store.get_events.call_args[1]
        assert call_kwargs['user_id'] == 1
        assert call_kwargs['event_type'] == 'VendaFinalizada'
        assert call_kwargs['from_sequence'] == 100
        assert stats.filters_applied['user_id'] == 1


class TestReplayModeContext:
    """Testes do contexto de replay_mode"""
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_mode_ativo_durante_processamento(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: replay_mode deve estar ativo durante o replay"""
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': create_venda_criada_payload(1)
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
        assert len(replay_mode_during_processing) > 0
        assert all(replay_mode_during_processing)  # Estava True durante processamento
        assert is_replay_mode() is False  # Desativado após replay
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_mode_desativado_apos_erro(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: replay_mode deve ser desativado mesmo em caso de erro"""
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': create_venda_criada_payload(1)
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


class TestReplayBatching:
    """Testes de processamento em batches"""
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_processa_em_batches(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: Replay deve processar múltiplos batches"""
        # Arrange - criar 2500 eventos para 3 batches
        eventos = []
        for i in range(2500):
            eventos.append({
                'id': str(i),
                'sequence_number': i,
                'event_type': 'VendaCriada',
                'payload': create_venda_criada_payload(i)
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
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_faz_rollback_em_erro(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: Erro em batch deve causar rollback"""
        # Arrange
        eventos = [
            {
                'id': '1',
                'sequence_number': 1,
                'event_type': 'VendaCriada',
                'payload': create_venda_criada_payload(1)
            },
            {
                'id': '2',
                'sequence_number': 2,
                'event_type': 'VendaCriada',
                'payload': create_venda_criada_payload(2)
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


class TestReplayStats:
    """Testes das estatísticas de replay"""
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.VendaReadModelHandler')
    @patch('app.replay.engine.EventStore')
    def test_replay_retorna_estatisticas_completas(
        self,
        mock_store_class,
        mock_handler_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: Replay deve retornar estatísticas corretas"""
        # Arrange
        eventos = [
            {'id': str(i), 'sequence_number': i, 'event_type': 'VendaCriada',
             'payload': create_venda_criada_payload(i)}
            for i in range(100)
        ]
        
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
    
    @patch('app.replay.engine._log_replay_end')
    @patch('app.replay.engine._log_replay_start')
    @patch('app.replay.engine.EventStore')
    def test_replay_sem_eventos_retorna_stats_vazio(
        self,
        mock_store_class,
        mock_log_start,
        mock_log_end,
        db_session
    ):
        """✅ Teste: Replay sem eventos deve retornar stats zerado"""
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
