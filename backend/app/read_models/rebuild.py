"""
Rebuild Manager - Integração Replay Engine + Schema Swap
=========================================================

Orquestra o rebuild completo de read models sem downtime.

FLUXO:
1. Cria schema temporário
2. Replay de eventos no schema temporário
3. Validação do schema temporário
4. Swap atômico
5. Cleanup

GARANTIAS:
- Sistema continua operacional durante rebuild
- Zero downtime
- Rollback seguro em caso de erro
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.read_models.schema_swap import (
    create_temp_schema,
    drop_temp_schema,
    validate_schema,
    swap_schemas_atomic,
    SwapResult,
    SchemaValidation
)
from app.replay import replay_events, ReplayStats

logger = logging.getLogger(__name__)


@dataclass
class RebuildResult:
    """Resultado do rebuild completo"""
    success: bool
    duration_seconds: float
    replay_stats: Optional[ReplayStats] = None
    swap_result: Optional[SwapResult] = None
    validation: Optional[SchemaValidation] = None
    error: Optional[str] = None
    phase_reached: str = "not_started"  # Fase onde parou
    
    def to_dict(self):
        return {
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'replay_stats': self.replay_stats.to_dict() if self.replay_stats else None,
            'swap_result': self.swap_result.to_dict() if self.swap_result else None,
            'validation': self.validation.to_dict() if self.validation else None,
            'error': self.error,
            'phase_reached': self.phase_reached
        }


def rebuild_read_models_zero_downtime(
    db: Session,
    user_id: Optional[int] = None,
    batch_size: int = 1000,
    validate_before_swap: bool = True
) -> RebuildResult:
    """
    Rebuild completo de read models com zero downtime.
    
    IMPORTANTE:
    - Sistema permanece operacional durante todo o processo
    - Leituras continuam no schema atual até o swap
    - Escritas normais continuam no schema atual
    - Apenas no momento do swap há uma breve pausa
    
    Args:
        db: Sessão do banco
        user_id: Filtrar replay por tenant (None = todos)
        batch_size: Tamanho do batch para replay
        validate_before_swap: Se deve validar antes do swap
    
    Returns:
        RebuildResult: Resultado completo do rebuild
    
    Example:
        >>> result = rebuild_read_models_zero_downtime(db)
        >>> if result.success:
        ...     logger.info(f"Rebuild concluído em {result.duration_seconds}s")
    """
    start_time = datetime.now(timezone.utc)
    phase = "not_started"
    
    try:
        logger.info("="*70)
        logger.info("🚀 INICIANDO REBUILD ZERO DOWNTIME")
        logger.info("="*70)
        
        # FASE 1: Criar schema temporário
        phase = "creating_temp_schema"
        logger.info(f"\n{'='*70}")
        logger.info("FASE 1: Criando Schema Temporário")
        logger.info("="*70)
        
        create_temp_schema(db)
        logger.info("✅ Schema temporário criado")
        
        # FASE 2: Replay de eventos no schema temporário
        phase = "replaying_events"
        logger.info(f"\n{'='*70}")
        logger.info("FASE 2: Replay de Eventos (Schema Temporário)")
        logger.info("="*70)
        logger.info("ℹ️  Sistema continua operacional normalmente...")
        
        # Aqui modificamos temporariamente as tabelas usadas pelos handlers
        # para apontar para as tabelas temporárias
        with _temp_schema_context(db):
            replay_stats = replay_events(
                db,
                user_id=user_id,
                batch_size=batch_size
            )
        
        if not replay_stats.success:
            error_msg = f"Replay falhou: {replay_stats.error}"
            logger.error(f"❌ {error_msg}")
            
            # Cleanup: remover schema temporário
            drop_temp_schema(db)
            
            return RebuildResult(
                success=False,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                replay_stats=replay_stats,
                error=error_msg,
                phase_reached=phase
            )
        
        logger.info(f"✅ Replay concluído: {replay_stats.total_events} eventos processados")
        
        # FASE 3: Validação do schema temporário
        phase = "validating_temp_schema"
        logger.info(f"\n{'='*70}")
        logger.info("FASE 3: Validando Schema Temporário")
        logger.info("="*70)
        
        validation = validate_schema(db, use_temp=True)
        
        if not validation.is_valid:
            error_msg = f"Schema temporário inválido: {validation.errors}"
            logger.error(f"❌ {error_msg}")
            
            # Cleanup
            drop_temp_schema(db)
            
            return RebuildResult(
                success=False,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                replay_stats=replay_stats,
                validation=validation,
                error=error_msg,
                phase_reached=phase
            )
        
        logger.info("✅ Schema temporário validado")
        
        # FASE 4: Swap atômico
        phase = "swapping_schemas"
        logger.info(f"\n{'='*70}")
        logger.info("FASE 4: Swap Atômico de Schemas")
        logger.info("="*70)
        logger.info("⚡ Executando swap (operação rápida)...")
        
        swap_result = swap_schemas_atomic(db, validate_before=validate_before_swap)
        
        if not swap_result.success:
            error_msg = f"Swap falhou: {swap_result.error}"
            logger.error(f"❌ {error_msg}")
            
            # Tentar cleanup (schema temporário pode ter virado _old)
            try:
                drop_temp_schema(db)
            except:
                pass
            
            return RebuildResult(
                success=False,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                replay_stats=replay_stats,
                swap_result=swap_result,
                validation=validation,
                error=error_msg,
                phase_reached=phase
            )
        
        logger.info("✅ Swap concluído com sucesso")
        
        # FASE 5: Conclusão
        phase = "completed"
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"\n{'='*70}")
        logger.info("✅ REBUILD CONCLUÍDO COM SUCESSO!")
        logger.info("="*70)
        logger.info(f"⏱️  Duração total: {duration:.2f}s")
        logger.info(f"📊 Eventos reprocessados: {replay_stats.total_events}")
        logger.info(f"📦 Tabelas atualizadas: {', '.join(swap_result.tables_swapped)}")
        logger.info("="*70)
        
        result = RebuildResult(
            success=True,
            duration_seconds=duration,
            replay_stats=replay_stats,
            swap_result=swap_result,
            validation=validation,
            phase_reached=phase
        )
        
        # Registrar auditoria
        _log_rebuild_success(db, result)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro fatal no rebuild: {e}", exc_info=True)
        
        # Tentar cleanup
        try:
            logger.info("🧹 Executando cleanup após erro...")
            drop_temp_schema(db)
        except Exception as cleanup_error:
            logger.error(f"❌ Erro no cleanup: {cleanup_error}")
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        result = RebuildResult(
            success=False,
            duration_seconds=duration,
            error=str(e),
            phase_reached=phase
        )
        
        # Registrar auditoria
        _log_rebuild_failure(db, result)
        
        return result


class _temp_schema_context:
    """
    Context manager para temporariamente redirecionar handlers
    para schema temporário.
    
    IMPORTANTE: Não modifica o replay engine, apenas o comportamento
    dos handlers durante o contexto.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.original_table_names = {}
    
    def __enter__(self):
        """Redireciona handlers para schema temporário"""
        from app.read_models import models
        
        logger.info("🔀 Redirecionando handlers para schema temporário...")
        
        # Salvar nomes originais e modificar para _temp
        for model_class in [models.VendasResumoDiario, models.PerformanceParceiro, models.ReceitaMensal]:
            original_name = model_class.__tablename__
            self.original_table_names[model_class] = original_name
            model_class.__tablename__ = f"{original_name}_temp"
        
        # Recriar o mapeamento (importante para SQLAlchemy)
        from app.db import Base
        Base.metadata.clear()
        
        logger.info("✅ Handlers redirecionados para schema temporário")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restaura nomes originais das tabelas"""
        from app.read_models import models
        
        logger.info("🔀 Restaurando nomes originais das tabelas...")
        
        # Restaurar nomes originais
        for model_class, original_name in self.original_table_names.items():
            model_class.__tablename__ = original_name
        
        # Recriar o mapeamento
        from app.db import Base
        Base.metadata.clear()
        
        logger.info("✅ Nomes originais restaurados")
        return False


def _log_rebuild_success(db: Session, result: RebuildResult) -> None:
    """Registra rebuild bem-sucedido em audit_log"""
    try:
        import json
        from app.audit_log import log_action
        
        log_action(
            db=db,
            user_id=None,
            action='rebuild_read_models_success',
            entity_type='read_models',
            entity_id=None,
            details=json.dumps({
                'duration_seconds': result.duration_seconds,
                'events_processed': result.replay_stats.total_events if result.replay_stats else 0,
                'tables_updated': result.swap_result.tables_swapped if result.swap_result else [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        )
        db.commit()
        
    except Exception as e:
        logger.warning(f"⚠️  Falha ao registrar auditoria: {e}")
        db.rollback()


def _log_rebuild_failure(db: Session, result: RebuildResult) -> None:
    """Registra falha de rebuild em audit_log"""
    try:
        import json
        from app.audit_log import log_action
        
        log_action(
            db=db,
            user_id=None,
            action='rebuild_read_models_failure',
            entity_type='read_models',
            entity_id=None,
            details=json.dumps({
                'error': result.error,
                'phase_reached': result.phase_reached,
                'duration_seconds': result.duration_seconds,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        )
        db.commit()
        
    except Exception as e:
        logger.warning(f"⚠️  Falha ao registrar auditoria de erro: {e}")
        db.rollback()
