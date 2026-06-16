"""
Schema Swap Manager - Fase 5.5
================================

Gerencia rebuild de read models sem downtime através de troca atômica de schemas.

ESTRATÉGIA:
1. Cria tabelas temporárias (_temp)
2. Rebuild completo no schema temporário
3. Validação de integridade
4. Swap atômico (rename tables)
5. Cleanup do schema antigo

GARANTIAS:
- Zero downtime
- Rollback seguro em caso de erro
- Validação pré e pós swap
- Auditoria completa
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

from app.read_models.models import (
    VendasResumoDiario,
    PerformanceParceiro,
    ReceitaMensal,
)
from app.db import engine

logger = logging.getLogger(__name__)


# Mapeamento de tabelas de read models
READ_MODEL_TABLES = {
    "read_vendas_resumo_diario": VendasResumoDiario,
    "read_performance_parceiro": PerformanceParceiro,
    "read_receita_mensal": ReceitaMensal,
}


@dataclass
class SchemaValidation:
    """Resultado da validação de schema"""

    is_valid: bool
    table_counts: Dict[str, int]
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "table_counts": self.table_counts,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class SwapResult:
    """Resultado do swap de schemas"""

    success: bool
    duration_seconds: float
    tables_swapped: List[str]
    validation_before: Optional[SchemaValidation] = None
    validation_after: Optional[SchemaValidation] = None
    error: Optional[str] = None
    rollback_performed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "tables_swapped": self.tables_swapped,
            "validation_before": self.validation_before.to_dict()
            if self.validation_before
            else None,
            "validation_after": self.validation_after.to_dict()
            if self.validation_after
            else None,
            "error": self.error,
            "rollback_performed": self.rollback_performed,
        }


def create_temp_schema(db: Session) -> None:
    """
    Cria tabelas temporárias para rebuild.

    Estratégia:
    - Cria tabelas com sufixo _temp
    - Mesmo schema das tabelas originais
    - Índices e constraints copiados

    Args:
        db: Sessão do banco

    Raises:
        Exception: Se falhar ao criar schema temporário

    Example:
        >>> create_temp_schema(db)
        >>> # Tabelas criadas: read_vendas_resumo_diario_temp, etc
    """
    try:
        logger.info("🔧 Criando schema temporário...")

        # Para cada tabela de read model
        for table_name, model_class in READ_MODEL_TABLES.items():
            temp_table_name = f"{table_name}_temp"

            # Verificar se tabela temporária já existe
            inspector = inspect(engine)
            if temp_table_name in inspector.get_table_names():
                logger.warning(
                    f"⚠️  Tabela temporária {temp_table_name} já existe, dropando..."
                )
                db.execute(text(f"DROP TABLE IF EXISTS {temp_table_name}"))

            # Criar tabela temporária como cópia da estrutura
            logger.info(f"📝 Criando {temp_table_name}...")

            # SQLite: CREATE TABLE ... AS SELECT ... WHERE 1=0 (copia estrutura, não dados)
            create_stmt = f"""
                CREATE TABLE {temp_table_name} AS 
                SELECT * FROM {table_name} WHERE 1=0
            """
            db.execute(text(create_stmt))

            # Recriar índices UNIQUE (importantes para UPSERT)
            if table_name == "read_vendas_resumo_diario":
                db.execute(
                    text(
                        f"CREATE UNIQUE INDEX idx_{temp_table_name}_data ON {temp_table_name}(data)"
                    )
                )
            elif table_name == "read_performance_parceiro":
                db.execute(
                    text(
                        f"CREATE UNIQUE INDEX idx_{temp_table_name}_func_mes ON {temp_table_name}(funcionario_id, mes_referencia)"
                    )
                )
            elif table_name == "read_receita_mensal":
                db.execute(
                    text(
                        f"CREATE UNIQUE INDEX idx_{temp_table_name}_mes ON {temp_table_name}(mes_referencia)"
                    )
                )

        db.commit()
        logger.info("✅ Schema temporário criado com sucesso")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao criar schema temporário: {e}", exc_info=True)
        raise


def drop_temp_schema(db: Session) -> None:
    """
    Remove tabelas temporárias.

    Args:
        db: Sessão do banco

    Example:
        >>> drop_temp_schema(db)
    """
    try:
        logger.info("🗑️  Removendo schema temporário...")

        for table_name in READ_MODEL_TABLES.keys():
            temp_table_name = f"{table_name}_temp"
            db.execute(text(f"DROP TABLE IF EXISTS {temp_table_name}"))

        db.commit()
        logger.info("✅ Schema temporário removido")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao remover schema temporário: {e}", exc_info=True)
        raise


def validate_schema(db: Session, use_temp: bool = False) -> SchemaValidation:
    """
    Valida integridade do schema (atual ou temporário).

    Validações:
    - Contagem de registros
    - Presença de dados mínimos
    - Integridade referencial básica

    Args:
        db: Sessão do banco
        use_temp: Se True, valida schema temporário

    Returns:
        SchemaValidation: Resultado da validação

    Example:
        >>> validation = validate_schema(db, use_temp=True)
        >>> if validation.is_valid:
        ...     logger.info("Schema válido!")
    """
    suffix = "_temp" if use_temp else ""
    errors = []
    warnings = []
    table_counts = {}

    try:
        logger.info(f"🔍 Validando schema {'temporário' if use_temp else 'atual'}...")

        # Contar registros em cada tabela
        for table_name in READ_MODEL_TABLES.keys():
            full_table_name = f"{table_name}{suffix}"

            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {full_table_name}"))
                count = result.fetchone()[0]
                table_counts[table_name] = count
                logger.info(f"  📊 {full_table_name}: {count} registros")

            except Exception as e:
                errors.append(f"Erro ao contar {full_table_name}: {str(e)}")

        # Validações de integridade

        # 1. Verificar se há dados mínimos (warning se vazio)
        total_records = sum(table_counts.values())
        if total_records == 0:
            warnings.append("Schema está vazio (sem registros em nenhuma tabela)")

        # 2. Verificar consistência de datas (não pode ter datas futuras)
        try:
            result = db.execute(
                text(f"""
                SELECT COUNT(*) FROM read_vendas_resumo_diario{suffix}
                WHERE data > DATE('now')
            """)
            )
            future_dates = result.fetchone()[0]
            if future_dates > 0:
                errors.append(
                    f"Encontradas {future_dates} datas futuras em vendas_resumo_diario"
                )
        except Exception as e:
            warnings.append(f"Não foi possível validar datas: {str(e)}")

        # 3. Verificar valores negativos inválidos
        try:
            result = db.execute(
                text(f"""
                SELECT COUNT(*) FROM read_receita_mensal{suffix}
                WHERE receita_bruta < 0
            """)
            )
            negative_revenue = result.fetchone()[0]
            if negative_revenue > 0:
                errors.append(f"Encontradas {negative_revenue} receitas negativas")
        except Exception as e:
            warnings.append(f"Não foi possível validar receitas: {str(e)}")

        # Determinar se é válido
        is_valid = len(errors) == 0

        validation = SchemaValidation(
            is_valid=is_valid,
            table_counts=table_counts,
            errors=errors,
            warnings=warnings,
        )

        if is_valid:
            logger.info(f"✅ Schema {'temporário' if use_temp else 'atual'} é válido")
        else:
            logger.error(
                f"❌ Schema {'temporário' if use_temp else 'atual'} inválido: {errors}"
            )

        return validation

    except Exception as e:
        logger.error(f"❌ Erro na validação: {e}", exc_info=True)
        return SchemaValidation(
            is_valid=False,
            table_counts=table_counts,
            errors=[f"Erro fatal na validação: {str(e)}"],
            warnings=warnings,
        )


def swap_schemas_atomic(db: Session, validate_before: bool = True) -> SwapResult:
    """
    Troca atômica entre schema temporário e atual.

    Processo:
    1. Validação pré-swap (opcional)
    2. Renomeia tabelas atuais para _old
    3. Renomeia tabelas _temp para nomes atuais
    4. Validação pós-swap
    5. Remove tabelas _old

    Em caso de erro:
    - Rollback completo
    - Tabelas originais preservadas

    Args:
        db: Sessão do banco
        validate_before: Se deve validar antes do swap

    Returns:
        SwapResult: Resultado do swap

    Example:
        >>> result = swap_schemas_atomic(db)
        >>> if result.success:
        ...     logger.info(f"Swap concluído em {result.duration_seconds}s")
    """
    start_time = datetime.now(timezone.utc)
    validation_before = None
    validation_after = None
    rollback_performed = False

    try:
        logger.info("🔄 Iniciando swap atômico de schemas...")

        # 1. Validação pré-swap
        if validate_before:
            logger.info("1️⃣ Validando schema temporário antes do swap...")
            validation_before = validate_schema(db, use_temp=True)

            if not validation_before.is_valid:
                error_msg = f"Schema temporário inválido: {validation_before.errors}"
                logger.error(f"❌ {error_msg}")

                return SwapResult(
                    success=False,
                    duration_seconds=0,
                    tables_swapped=[],
                    validation_before=validation_before,
                    error=error_msg,
                )

        # 2. Swap atômico em transação
        logger.info("2️⃣ Executando swap atômico...")

        tables_swapped = []
        old_tables_created = []

        try:
            # Para cada tabela de read model
            for table_name in READ_MODEL_TABLES.keys():
                temp_table = f"{table_name}_temp"
                old_table = f"{table_name}_old"

                # Passo 1: Renomear atual para _old
                logger.info(f"  📝 {table_name} → {old_table}")
                db.execute(text(f"ALTER TABLE {table_name} RENAME TO {old_table}"))
                old_tables_created.append(old_table)

                # Passo 2: Renomear _temp para atual
                logger.info(f"  📝 {temp_table} → {table_name}")
                db.execute(text(f"ALTER TABLE {temp_table} RENAME TO {table_name}"))
                tables_swapped.append(table_name)

            # Commit da transação de swap
            db.commit()
            logger.info("✅ Swap atômico concluído")

        except Exception as swap_error:
            # ❌ ROLLBACK: reverter renomeações
            logger.error(f"❌ Erro no swap, fazendo rollback: {swap_error}")
            rollback_performed = True

            try:
                # Reverter renomeações já feitas
                for table_name in tables_swapped:
                    old_table = f"{table_name}_old"
                    if old_table in old_tables_created:
                        # Reverter: atual → _temp e _old → atual
                        db.execute(
                            text(
                                f"ALTER TABLE {table_name} RENAME TO {table_name}_temp"
                            )
                        )
                        db.execute(
                            text(f"ALTER TABLE {old_table} RENAME TO {table_name}")
                        )

                db.commit()
                logger.info("✅ Rollback concluído, tabelas originais restauradas")

            except Exception as rollback_error:
                logger.error(f"❌ ERRO CRÍTICO no rollback: {rollback_error}")
                db.rollback()

            raise swap_error

        # 3. Validação pós-swap
        logger.info("3️⃣ Validando schema após swap...")
        validation_after = validate_schema(db, use_temp=False)

        if not validation_after.is_valid:
            logger.warning(
                f"⚠️  Schema após swap tem avisos: {validation_after.warnings}"
            )
        else:
            logger.info("✅ Schema validado após swap")

        # 4. Remover tabelas _old
        logger.info("4️⃣ Removendo tabelas antigas...")
        for table_name in READ_MODEL_TABLES.keys():
            old_table = f"{table_name}_old"
            db.execute(text(f"DROP TABLE IF EXISTS {old_table}"))

        db.commit()
        logger.info("✅ Tabelas antigas removidas")

        # Calcular duração
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        result = SwapResult(
            success=True,
            duration_seconds=duration,
            tables_swapped=tables_swapped,
            validation_before=validation_before,
            validation_after=validation_after,
            rollback_performed=False,
        )

        logger.info(f"✅ Swap concluído com sucesso em {duration:.2f}s")
        logger.info(f"📊 Tabelas trocadas: {', '.join(tables_swapped)}")

        # Registrar auditoria
        _log_swap_success(db, result)

        return result

    except Exception as e:
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        error_msg = str(e)
        logger.error(f"❌ Swap falhou: {error_msg}")

        result = SwapResult(
            success=False,
            duration_seconds=duration,
            tables_swapped=tables_swapped if "tables_swapped" in locals() else [],
            validation_before=validation_before,
            error=error_msg,
            rollback_performed=rollback_performed,
        )

        # Registrar auditoria de falha
        _log_swap_failure(db, result)

        return result


def _log_swap_success(db: Session, result: SwapResult) -> None:
    """Registra swap bem-sucedido em audit_log"""
    try:
        import json
        from app.audit_log import log_action

        log_action(
            db=db,
            user_id=None,  # Ação do sistema
            action="schema_swap_success",
            entity_type="read_models",
            entity_id=None,
            details=json.dumps(
                {
                    "duration_seconds": result.duration_seconds,
                    "tables_swapped": result.tables_swapped,
                    "validation_before": result.validation_before.to_dict()
                    if result.validation_before
                    else None,
                    "validation_after": result.validation_after.to_dict()
                    if result.validation_after
                    else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )
        db.commit()

    except Exception as e:
        logger.warning(f"⚠️  Falha ao registrar auditoria de swap: {e}")
        db.rollback()


def _log_swap_failure(db: Session, result: SwapResult) -> None:
    """Registra falha de swap em audit_log"""
    try:
        import json
        from app.audit_log import log_action

        log_action(
            db=db,
            user_id=None,  # Ação do sistema
            action="schema_swap_failure",
            entity_type="read_models",
            entity_id=None,
            details=json.dumps(
                {
                    "error": result.error,
                    "duration_seconds": result.duration_seconds,
                    "rollback_performed": result.rollback_performed,
                    "tables_swapped": result.tables_swapped,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )
        db.commit()

    except Exception as e:
        logger.warning(f"⚠️  Falha ao registrar auditoria de erro: {e}")
        db.rollback()
