"""
Testes do Schema Swap - Fase 5.5
=================================

Valida:
- Criação e remoção de schema temporário
- Validação de schema
- Swap atômico
- Rollback em caso de erro
- Rebuild completo zero downtime
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.read_models.schema_swap import (
    create_temp_schema,
    drop_temp_schema,
    validate_schema,
    swap_schemas_atomic,
    SchemaValidation,
    SwapResult,
    READ_MODEL_TABLES
)
from app.read_models.rebuild import (
    rebuild_read_models_zero_downtime,
    RebuildResult
)


@pytest.fixture
def db_session():
    """Mock de sessão do banco"""
    session = Mock(spec=Session)
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


class TestSchemaCreation:
    """Testes de criação de schema temporário"""
    
    @patch('app.read_models.schema_swap.inspect')
    @patch('app.read_models.schema_swap.engine')
    def test_create_temp_schema_success(self, mock_engine, mock_inspect, db_session):
        """✅ Teste: Criação de schema temporário bem-sucedida"""
        # Arrange
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = []
        mock_inspect.return_value = mock_inspector
        
        # Act
        create_temp_schema(db_session)
        
        # Assert
        assert db_session.execute.called
        assert db_session.commit.called
    
    def test_drop_temp_schema_success(self, db_session):
        """✅ Teste: Remoção de schema temporário bem-sucedida"""
        # Act
        drop_temp_schema(db_session)
        
        # Assert
        assert db_session.execute.called
        assert db_session.commit.called


class TestSchemaValidation:
    """Testes de validação de schema"""
    
    def test_validate_schema_with_data(self, db_session):
        """✅ Teste: Validação de schema com dados"""
        # Arrange
        call_count = [0]
        
        def mock_execute(query):
            call_count[0] += 1
            result = Mock()
            
            # Contagens de tabelas: retorna 100
            if 'COUNT(*)' in str(query) and 'WHERE' not in str(query):
                result.fetchone.return_value = [100]
            # Validações (datas futuras, receitas negativas): retorna 0 (sem erros)
            else:
                result.fetchone.return_value = [0]
            
            return result
        
        db_session.execute.side_effect = mock_execute
        
        # Act
        validation = validate_schema(db_session, use_temp=False)
        
        # Assert
        assert isinstance(validation, SchemaValidation)
        assert validation.is_valid is True
    
    def test_validate_schema_empty(self, db_session):
        """✅ Teste: Validação de schema vazio gera warning"""
        # Arrange
        mock_result = Mock()
        mock_result.fetchone.return_value = [0]  # 0 registros
        db_session.execute.return_value = mock_result
        
        # Act
        validation = validate_schema(db_session, use_temp=True)
        
        # Assert
        assert len(validation.warnings) > 0
        assert 'vazio' in validation.warnings[0].lower()
    
    def test_validate_schema_detects_future_dates(self, db_session):
        """✅ Teste: Validação detecta datas futuras"""
        # Arrange
        call_count = [0]
        
        def mock_execute(query):
            call_count[0] += 1
            result = Mock()
            
            # Primeira chamada: contagem de tabelas (3 tabelas, retorna 0)
            # Quarta chamada: datas futuras
            if 'WHERE data >' in str(query):
                result.fetchone.return_value = [5]  # 5 datas futuras
            else:
                result.fetchone.return_value = [0]
            
            return result
        
        db_session.execute.side_effect = mock_execute
        
        # Act
        validation = validate_schema(db_session)
        
        # Assert
        assert not validation.is_valid
        assert any('data' in error.lower() and 'futura' in error.lower() 
                   for error in validation.errors)


class TestSchemaSwap:
    """Testes de swap atômico"""
    
    @patch('app.read_models.schema_swap.validate_schema')
    @patch('app.read_models.schema_swap._log_swap_success')
    def test_swap_schemas_success(
        self, 
        mock_log_success,
        mock_validate,
        db_session
    ):
        """✅ Teste: Swap atômico bem-sucedido"""
        # Arrange
        mock_validate.return_value = SchemaValidation(
            is_valid=True,
            table_counts={'table1': 100},
            errors=[],
            warnings=[]
        )
        
        # Act
        result = swap_schemas_atomic(db_session, validate_before=True)
        
        # Assert
        assert isinstance(result, SwapResult)
        assert result.success is True
        assert len(result.tables_swapped) > 0
        assert not result.rollback_performed
        assert db_session.commit.called
    
    @patch('app.read_models.schema_swap.validate_schema')
    @patch('app.read_models.schema_swap._log_swap_failure')
    def test_swap_schemas_fails_validation(
        self,
        mock_log_failure,
        mock_validate,
        db_session
    ):
        """✅ Teste: Swap abortado se validação falhar"""
        # Arrange
        mock_validate.return_value = SchemaValidation(
            is_valid=False,
            table_counts={},
            errors=['Schema inválido'],
            warnings=[]
        )
        
        # Act
        result = swap_schemas_atomic(db_session, validate_before=True)
        
        # Assert
        assert result.success is False
        assert result.error is not None
        assert 'inválido' in result.error.lower()
    
    @patch('app.read_models.schema_swap.validate_schema')
    def test_swap_schemas_rollback_on_error(
        self,
        mock_validate,
        db_session
    ):
        """✅ Teste: Rollback em caso de erro no swap"""
        # Arrange
        mock_validate.return_value = SchemaValidation(
            is_valid=True,
            table_counts={'table1': 100},
            errors=[],
            warnings=[]
        )
        
        # Simular erro no meio do swap
        call_count = [0]
        
        def mock_execute_with_error(query):
            call_count[0] += 1
            # Falha na segunda renomeação
            if call_count[0] == 2:
                raise Exception("Erro simulado no swap")
            return Mock()
        
        db_session.execute.side_effect = mock_execute_with_error
        
        # Act
        result = swap_schemas_atomic(db_session)
        
        # Assert
        assert result.success is False
        assert result.rollback_performed is True


class TestRebuildComplete:
    """Testes de rebuild completo"""
    
    @patch('app.read_models.rebuild._log_rebuild_success')
    @patch('app.read_models.rebuild.swap_schemas_atomic')
    @patch('app.read_models.rebuild.validate_schema')
    @patch('app.read_models.rebuild.replay_events')
    @patch('app.read_models.rebuild.create_temp_schema')
    def test_rebuild_zero_downtime_success(
        self,
        mock_create_temp,
        mock_replay,
        mock_validate,
        mock_swap,
        mock_log,
        db_session
    ):
        """✅ Teste: Rebuild completo bem-sucedido"""
        # Arrange
        from app.replay import ReplayStats
        
        mock_replay.return_value = ReplayStats(
            total_events=1000,
            batches_processed=1,
            duration_seconds=10.0,
            success=True
        )
        
        mock_validate.return_value = SchemaValidation(
            is_valid=True,
            table_counts={'table1': 1000},
            errors=[],
            warnings=[]
        )
        
        mock_swap.return_value = SwapResult(
            success=True,
            duration_seconds=0.5,
            tables_swapped=['table1', 'table2']
        )
        
        # Act
        result = rebuild_read_models_zero_downtime(db_session)
        
        # Assert
        assert isinstance(result, RebuildResult)
        assert result.success is True
        assert result.phase_reached == 'completed'
        assert result.replay_stats is not None
        assert result.swap_result is not None
    
    @patch('app.read_models.rebuild.drop_temp_schema')
    @patch('app.read_models.rebuild._log_rebuild_failure')
    @patch('app.read_models.rebuild.replay_events')
    @patch('app.read_models.rebuild.create_temp_schema')
    def test_rebuild_fails_on_replay_error(
        self,
        mock_create_temp,
        mock_replay,
        mock_log,
        mock_drop,
        db_session
    ):
        """✅ Teste: Rebuild falha se replay tiver erro"""
        # Arrange
        from app.replay import ReplayStats
        
        mock_replay.return_value = ReplayStats(
            total_events=0,
            batches_processed=0,
            duration_seconds=1.0,
            success=False,
            error='Erro no replay'
        )
        
        # Act
        result = rebuild_read_models_zero_downtime(db_session)
        
        # Assert
        assert result.success is False
        assert result.phase_reached == 'replaying_events'
        assert 'replay' in result.error.lower()
        
        # Deve ter feito cleanup
        assert mock_drop.called
    
    @patch('app.read_models.rebuild.drop_temp_schema')
    @patch('app.read_models.rebuild._log_rebuild_failure')
    @patch('app.read_models.rebuild.validate_schema')
    @patch('app.read_models.rebuild.replay_events')
    @patch('app.read_models.rebuild.create_temp_schema')
    def test_rebuild_fails_on_validation_error(
        self,
        mock_create_temp,
        mock_replay,
        mock_validate,
        mock_log,
        mock_drop,
        db_session
    ):
        """✅ Teste: Rebuild falha se validação detectar erro"""
        # Arrange
        from app.replay import ReplayStats
        
        mock_replay.return_value = ReplayStats(
            total_events=1000,
            batches_processed=1,
            duration_seconds=10.0,
            success=True
        )
        
        mock_validate.return_value = SchemaValidation(
            is_valid=False,
            table_counts={},
            errors=['Dados inconsistentes'],
            warnings=[]
        )
        
        # Act
        result = rebuild_read_models_zero_downtime(db_session)
        
        # Assert
        assert result.success is False
        assert result.phase_reached == 'validating_temp_schema'
        assert result.validation is not None
        
        # Deve ter feito cleanup
        assert mock_drop.called


class TestTempSchemaContext:
    """Testes do context manager de schema temporário"""
    
    def test_temp_schema_context_redirects_handlers(self, db_session):
        """✅ Teste: Context manager redireciona handlers para schema temporário"""
        from app.read_models.rebuild import _temp_schema_context
        from app.read_models import models
        
        # Arrange
        original_name = models.VendasResumoDiario.__tablename__
        
        # Act & Assert
        with _temp_schema_context(db_session):
            # Durante o contexto, deve ter sufixo _temp
            assert models.VendasResumoDiario.__tablename__.endswith('_temp')
        
        # Após o contexto, deve voltar ao original
        assert models.VendasResumoDiario.__tablename__ == original_name


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
