"""
🔍 SQL AUDIT - Hook de Auditoria de RAW SQL
============================================

Hook SQLAlchemy que detecta execução de RAW SQL fora do helper tenant-safe.

⚠️ IMPORTANTE:
- Classifica risco (HIGH/MEDIUM/LOW)
- Coleta métricas em memória (total, by risk, by file, by table)
- PODE bloquear execução de queries HIGH risk (se enforcement ativo)
- Helper tenant-safe NUNCA é bloqueado

Autor: Sistema de Hardening Multi-Tenant
Data: 2026-02-05
Versão: 1.3.0
Fase: 1.4.3-D (Enforcement)
"""

import logging
import os
import traceback
from datetime import datetime
from typing import Any
from sqlalchemy import event
from sqlalchemy.engine import Engine, Connection

from app.db.sql_audit_classifier import (
    classify_raw_sql_risk,
    extract_table_names as _extract_table_names,
    is_raw_sql_text as _is_raw_sql_text,
    should_audit_statement as _should_audit_statement,
)
from app.db.sql_audit_config import (
    PROD_LIKE_ENVIRONMENTS,
    VALID_ENFORCEMENT_LEVELS,
    current_environment_name as _current_environment_name,
    env_truthy as _env_truthy,
    normalize_enforcement_level as _normalize_enforcement_level,
)
from app.db.sql_audit_metrics import (
    SNAPSHOT_INTERVAL,
    SQL_AUDIT_STATS,
    build_audit_stats,
    increment_stats as _increment_stats,
    log_snapshot as _log_snapshot,
    reset_stats as _reset_audit_stats,
)
from app.db.sql_audit_tables import TENANT_TABLES, WHITELIST_TABLES

__all__ = [
    "RawSQLEnforcementError",
    "PROD_LIKE_ENVIRONMENTS",
    "SNAPSHOT_INTERVAL",
    "SQL_AUDIT_ENFORCE",
    "SQL_AUDIT_ENFORCE_LEVEL",
    "SQL_AUDIT_ENFORCE_LEVEL_RAW",
    "SQL_AUDIT_ENVIRONMENT",
    "SQL_AUDIT_STATS",
    "TENANT_TABLES",
    "WHITELIST_TABLES",
    "_env_truthy",
    "_extract_table_names",
    "_normalize_enforcement_level",
    "audit_raw_sql",
    "classify_raw_sql_risk",
    "disable_sql_audit",
    "enable_sql_audit",
    "get_audit_stats",
    "get_enforcement_config",
    "is_enforcement_enabled",
    "reset_audit_stats",
]


# =============================================================================
# EXCEÇÕES - FASE 1.4.3-D
# =============================================================================


class RawSQLEnforcementError(RuntimeError):
    """
    Exceção lançada quando RAW SQL HIGH risk é bloqueado por enforcement.

    Enforcement pode ser ativado via variável de ambiente:
        SQL_AUDIT_ENFORCE=true
        SQL_AUDIT_ENFORCE_LEVEL=HIGH

    Esta exceção NUNCA é lançada para:
    - Queries do helper tenant-safe
    - Queries MEDIUM ou LOW risk
    - Quando enforcement está desativado
    """

    pass


# Configurar logger específico para auditoria SQL
logger = logging.getLogger("sql_audit")
logger.setLevel(logging.WARNING)  # WARNING para evitar spam de logs normais

# Se não há handlers, adicionar um básico
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)


# =============================================================================
# CONFIGURAÇÃO DE ENFORCEMENT - FASE 1.4.3-D
# =============================================================================

SQL_AUDIT_ENVIRONMENT = _current_environment_name()
SQL_AUDIT_ENFORCE = _env_truthy(
    "SQL_AUDIT_ENFORCE",
    default=SQL_AUDIT_ENVIRONMENT in PROD_LIKE_ENVIRONMENTS,
)
SQL_AUDIT_ENFORCE_LEVEL, SQL_AUDIT_ENFORCE_LEVEL_RAW = _normalize_enforcement_level(
    os.getenv("SQL_AUDIT_ENFORCE_LEVEL")
)

# Validar level
if SQL_AUDIT_ENFORCE_LEVEL_RAW not in VALID_ENFORCEMENT_LEVELS:
    logger.warning(
        f"⚠️  SQL_AUDIT_ENFORCE_LEVEL inválido: {SQL_AUDIT_ENFORCE_LEVEL_RAW}. "
        f"Usando default: HIGH"
    )
    SQL_AUDIT_ENFORCE_LEVEL = "HIGH"

# Log de configuração
if SQL_AUDIT_ENFORCE:
    logger.warning(
        f"🔒 SQL AUDIT ENFORCEMENT ATIVO - Bloqueando queries {SQL_AUDIT_ENFORCE_LEVEL}+"
    )
else:
    logger.info("🔓 SQL Audit enforcement desativado (apenas logging)")


def _get_call_origin() -> tuple[str, str, int]:
    """
    Identifica o arquivo, função e linha que originou a execução SQL.

    Returns:
        tuple[file, function, line]: Origem da chamada
    """
    stack = traceback.extract_stack()

    # Filtrar frames do próprio SQLAlchemy e deste módulo
    for frame in reversed(stack):
        filename = frame.filename

        # Ignorar frames internos
        if any(
            ignore in filename
            for ignore in [
                "sqlalchemy",
                "sql_audit.py",
                "contextlib.py",
                "threading.py",
            ]
        ):
            continue

        # Pegar primeiro frame de código do usuário
        # Extrair apenas o nome do arquivo (sem path completo)
        file_short = (
            filename.split("\\")[-1] if "\\" in filename else filename.split("/")[-1]
        )
        return (file_short, frame.name, frame.lineno)

    return ("unknown", "unknown", 0)


def _is_from_tenant_safe_helper(stack_trace: str) -> bool:
    """
    Verifica se a execução SQL veio do helper tenant_safe_sql.

    Args:
        stack_trace: String com traceback completo

    Returns:
        bool: True se veio do helper, False caso contrário
    """
    # Verificar se tenant_safe_sql está na call stack
    indicators = [
        "tenant_safe_sql.py",
        "execute_tenant_safe",
        "execute_tenant_safe_scalar",
        "execute_tenant_safe_one",
        "execute_tenant_safe_first",
        "execute_tenant_safe_all",
    ]

    return any(indicator in stack_trace for indicator in indicators)


@event.listens_for(Engine, "before_cursor_execute", retval=False)
def audit_raw_sql(
    conn: Connection,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    """
    Hook SQLAlchemy executado ANTES de cada query.

    Detecta RAW SQL executado fora do helper tenant-safe e registra para auditoria.

    ⚠️ IMPORTANTE: NÃO bloqueia execução, apenas registra.

    Args:
        conn: Conexão SQLAlchemy
        cursor: Cursor do banco
        statement: SQL statement a ser executado
        parameters: Parâmetros da query
        context: Contexto de execução
        executemany: Se é executemany
    """
    # Verificar se deve auditar
    if not _should_audit_statement(statement):
        return

    # Verificar se é RAW SQL
    if not _is_raw_sql_text(statement):
        return

    # Obter call stack completo
    stack_trace = "".join(traceback.format_stack())

    # Verificar se veio do helper tenant-safe
    if _is_from_tenant_safe_helper(stack_trace):
        # Query segura, não precisa auditar
        return

    # ALERTA: RAW SQL fora do helper!
    file_origin, func_origin, line_origin = _get_call_origin()

    # Classificar risco
    has_tenant_filter = "{tenant_filter}" in statement
    risk_level, tables_detected = classify_raw_sql_risk(statement, has_tenant_filter)

    # Incrementar métricas
    _increment_stats(risk_level, tables_detected, file_origin)

    # Logar snapshot a cada N eventos
    if SQL_AUDIT_STATS["total"] % SNAPSHOT_INTERVAL == 0:
        _log_snapshot()

    # =============================================================================
    # ENFORCEMENT - FASE 1.4.3-D
    # =============================================================================

    # Verificar se deve bloquear
    should_block = False

    if SQL_AUDIT_ENFORCE:
        # Determinar se risco atinge o threshold de enforcement
        risk_levels_order = ["LOW", "MEDIUM", "HIGH"]
        current_risk_index = (
            risk_levels_order.index(risk_level)
            if risk_level in risk_levels_order
            else 0
        )
        enforce_level_index = risk_levels_order.index(SQL_AUDIT_ENFORCE_LEVEL)

        should_block = current_risk_index >= enforce_level_index

    if should_block:
        # BLOQUEAR EXECUÇÃO
        tables_str = ", ".join(tables_detected) if tables_detected else "unknown"

        # Log de bloqueio
        logger.error(
            f"🚫 RAW SQL BLOCKED BY ENFORCEMENT - RISK: {risk_level}",
            extra={
                "event": "raw_sql_blocked",
                "timestamp": datetime.utcnow().isoformat(),
                "risk_level": risk_level,
                "tables_detected": tables_detected,
                "sql_truncated": statement[:200],
                "file_origin": file_origin,
                "function_origin": func_origin,
                "line_origin": line_origin,
                "enforcement_level": SQL_AUDIT_ENFORCE_LEVEL,
            },
        )

        # Lançar exceção com mensagem clara
        error_msg = (
            f"🚫 RAW SQL BLOCKED: {risk_level} risk query detected\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Origin: {file_origin}:{line_origin} in {func_origin}()\n"
            f"📊 Tables: {tables_str}\n"
            f"⚠️  Risk: {risk_level} (enforcement level: {SQL_AUDIT_ENFORCE_LEVEL})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Solution:\n"
            f"   Use tenant-safe helper:\n"
            f"   from app.utils.tenant_safe_sql import execute_tenant_safe\n"
            f"\n"
            f"   execute_tenant_safe(db, '''\n"
            f"       SELECT * FROM {tables_str}\n"
            f"       WHERE {{tenant_filter}} AND ...\n"
            f"   ''', {{...}})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📚 Docs: See CHANGES_RAW_SQL_INFRA_P0.md\n"
        )

        raise RawSQLEnforcementError(error_msg)

    # =============================================================================
    # LOGGING (se não foi bloqueado)
    # =============================================================================

    # Truncar SQL para log (evitar logs gigantes)
    sql_truncated = statement[:500]
    if len(statement) > 500:
        sql_truncated += f"... ({len(statement)} chars total)"

    # Escolher nível de log baseado no risco
    log_method = logger.error if risk_level == "HIGH" else logger.warning
    risk_emoji = (
        "🔴" if risk_level == "HIGH" else "🟡" if risk_level == "MEDIUM" else "🟢"
    )

    # Log estruturado
    log_method(
        f"{risk_emoji} RAW SQL OUTSIDE HELPER DETECTED - RISK: {risk_level}",
        extra={
            "event": "raw_sql_outside_helper",
            "timestamp": datetime.utcnow().isoformat(),
            "risk_level": risk_level,
            "tables_detected": tables_detected,
            "sql_truncated": sql_truncated,
            "sql_length": len(statement),
            "file_origin": file_origin,
            "function_origin": func_origin,
            "line_origin": line_origin,
            "has_parameters": bool(parameters),
            "executemany": executemany,
        },
    )

    # Log legível para console (desenvolvimento)
    tables_str = ", ".join(tables_detected) if tables_detected else "none"
    log_method(
        f"\n{'=' * 80}\n"
        f"{risk_emoji} RAW SQL OUTSIDE HELPER - RISK: {risk_level}\n"
        f"{'=' * 80}\n"
        f"📍 Origin: {file_origin}:{line_origin} in {func_origin}()\n"
        f"📊 Tables: {tables_str}\n"
        f"📝 SQL: {sql_truncated}\n"
        f"{'=' * 80}\n"
    )


def enable_sql_audit() -> None:
    """
    Habilita auditoria de RAW SQL.

    Deve ser chamado durante inicialização da aplicação:

    ```python
    from app.db.sql_audit import enable_sql_audit

    # No startup da aplicação
    enable_sql_audit()
    ```

    ⚠️ NOTA: O listener já é registrado automaticamente via decorator @event.listens_for
    Esta função existe apenas para documentação e possível configuração futura.
    """
    logger.info("✅ SQL Audit enabled - Monitoring RAW SQL execution")


def disable_sql_audit() -> None:
    """
    Desabilita auditoria de RAW SQL.

    Útil para testes ou ambientes onde auditoria não é necessária.
    """
    from sqlalchemy import event

    # Remover listener
    if event.contains(Engine, "before_cursor_execute", audit_raw_sql):
        event.remove(Engine, "before_cursor_execute", audit_raw_sql)
        logger.info("❌ SQL Audit disabled")


def get_audit_stats() -> dict:
    """
    Retorna estatísticas de auditoria em tempo real.

    Returns:
        dict: Métricas completas (total, by risk, by file, by table)
    """
    return build_audit_stats(
        listener_registered=event.contains(
            Engine, "before_cursor_execute", audit_raw_sql
        )
    )


def reset_audit_stats() -> None:
    """
    Reseta todas as métricas (útil para testes).
    """
    _reset_audit_stats()


def is_enforcement_enabled() -> bool:
    """
    Verifica se enforcement está ativo.

    Returns:
        bool: True se enforcement está ativo
    """
    return SQL_AUDIT_ENFORCE


def get_enforcement_config() -> dict:
    """
    Retorna configuração de enforcement.

    Returns:
        dict: Configuração atual (enabled, level)
    """
    return {
        "enabled": SQL_AUDIT_ENFORCE,
        "level": SQL_AUDIT_ENFORCE_LEVEL,
        "raw_level": SQL_AUDIT_ENFORCE_LEVEL_RAW,
        "environment": SQL_AUDIT_ENVIRONMENT,
        "blocks": f"{SQL_AUDIT_ENFORCE_LEVEL}+ risk queries"
        if SQL_AUDIT_ENFORCE
        else "none",
    }


# Auto-enable ao importar módulo
logger.info("🔍 SQL Audit module loaded - Hook registered")
