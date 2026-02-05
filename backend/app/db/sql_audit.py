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
import traceback
import re
import os
from datetime import datetime
from typing import Any, Optional, List, Tuple
from sqlalchemy import event
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.engine.cursor import CursorResult


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
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    logger.addHandler(handler)


# =============================================================================
# CONFIGURAÇÃO DE ENFORCEMENT - FASE 1.4.3-D
# =============================================================================

# Ler flags de ambiente
SQL_AUDIT_ENFORCE = os.getenv("SQL_AUDIT_ENFORCE", "false").lower() in ("true", "1", "yes")
SQL_AUDIT_ENFORCE_LEVEL = os.getenv("SQL_AUDIT_ENFORCE_LEVEL", "HIGH").upper()

# Validar level
if SQL_AUDIT_ENFORCE_LEVEL not in ("HIGH", "MEDIUM", "LOW"):
    logger.warning(
        f"⚠️  SQL_AUDIT_ENFORCE_LEVEL inválido: {SQL_AUDIT_ENFORCE_LEVEL}. "
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


# =============================================================================
# MÉTRICAS EM MEMÓRIA - FASE 1.4.3-C
# =============================================================================

SQL_AUDIT_STATS = {
    "total": 0,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0,
    "by_file": {},      # {"comissoes_routes.py": 42, ...}
    "by_table": {},     # {"comissoes_itens": 35, ...}
    "last_snapshot": None,
}

# Logar snapshot a cada N eventos
SNAPSHOT_INTERVAL = 50


# =============================================================================
# CLASSIFICAÇÃO DE RISCO - TABELAS
# =============================================================================

# Tabelas multi-tenant que OBRIGATORIAMENTE precisam de tenant_filter
TENANT_TABLES = {
    # Comissões (42 queries no inventário)
    "comissoes_itens",
    "comissoes_vendedores",
    "comissoes_configuracao",
    "comissoes_provisoes",
    "comissoes_estornos",
    
    # Vendas
    "vendas",
    "vendas_itens",
    "vendas_pagamentos",
    
    # Estoque
    "produtos",
    "produtos_historico_precos",
    "estoque_movimentacoes",
    "estoque_reservas",
    
    # Financeiro
    "contas_pagar",
    "contas_receber",
    "lancamentos_financeiros",
    "caixa_movimentacoes",
    "conciliacao_cartao",
    
    # Clientes/Pets
    "clientes",
    "pets",
    "agendamentos",
    
    # Notas Fiscais
    "notas_entrada",
    "notas_entrada_itens",
    "notas_saida",
    "notas_saida_itens",
    
    # Pedidos
    "pedidos_compra",
    "pedidos_compra_itens",
    
    # Configurações por tenant
    "usuarios",
    "funcionarios",
    "cargos",
    "permissions_users",
    
    # WhatsApp
    "whatsapp_messages",
    "whatsapp_contacts",
    "conversas_ia",
    
    # Relatórios
    "dre_lancamentos",
    "dre_plano_contas",
}

# Tabelas de sistema que NÃO precisam de tenant_filter
WHITELIST_TABLES = {
    # Autenticação e controle
    "tenants",
    "permissions",
    "roles",
    "sessions",
    
    # Sistema
    "alembic_version",
    "migrations",
    
    # Catálogos globais
    "fiscal_catalogo_produtos",
    "fiscal_estado_padrao",
    
    # PostgreSQL system
    "pg_catalog",
    "information_schema",
}


# =============================================================================
# FUNÇÕES DE CLASSIFICAÇÃO
# =============================================================================

def _extract_table_names(sql: str) -> List[str]:
    """
    Extrai nomes de tabelas do SQL usando regex simples.
    
    Ignora aliases curtos (1-2 chars como 'v', 'ci', 't1').
    
    Args:
        sql: SQL statement
        
    Returns:
        List[str]: Lista de nomes de tabelas encontrados
    """
    sql_lower = sql.lower()
    tables = []
    
    # Padrões comuns: FROM table, JOIN table, INTO table, UPDATE table
    patterns = [
        r'\bfrom\s+(\w+)',
        r'\bjoin\s+(\w+)',
        r'\binto\s+(\w+)',
        r'\bupdate\s+(\w+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, sql_lower)
        tables.extend(matches)
    
    # Filtrar aliases comuns (1-2 caracteres: v, ci, t1, etc.)
    # Tabelas reais geralmente têm 3+ caracteres
    tables = [t for t in tables if len(t) >= 3]
    
    # Remover duplicatas mantendo ordem
    seen = set()
    unique_tables = []
    for table in tables:
        if table not in seen:
            seen.add(table)
            unique_tables.append(table)
    
    return unique_tables


def classify_raw_sql_risk(sql: str, has_tenant_filter: bool = False) -> Tuple[str, List[str]]:
    """
    Classifica o risco de segurança de uma query RAW SQL.
    
    Níveis de Risco:
    - HIGH: Tabela multi-tenant SEM {tenant_filter} → VAZAMENTO DE DADOS
    - MEDIUM: RAW SQL fora do helper mas em tabela whitelist
    - LOW: Query de sistema, health check, admin
    
    Args:
        sql: SQL statement a ser classificado
        has_tenant_filter: Se a query contém {tenant_filter}
        
    Returns:
        Tuple[risk_level, tables_detected]:
            - risk_level: "HIGH", "MEDIUM" ou "LOW"
            - tables_detected: Lista de tabelas identificadas
    """
    sql_lower = sql.lower().strip()
    tables = _extract_table_names(sql)
    
    # === RISCO BAIXO (LOW) ===
    
    # 1. Queries de health check
    if any(pattern in sql_lower for pattern in [
        "select 1",
        "select version()",
        "show server_version",
        "pg_is_in_recovery",
    ]):
        return ("LOW", [])
    
    # 2. Queries de sistema PostgreSQL
    if any(pattern in sql_lower for pattern in [
        "pg_catalog",
        "information_schema",
        "pg_stat_",
        "pg_class",
    ]):
        return ("LOW", tables)
    
    # 3. Transações e controle
    if sql_lower in ["begin", "commit", "rollback", "savepoint"]:
        return ("LOW", [])
    
    # 4. Alembic migrations
    if "alembic_version" in sql_lower:
        return ("LOW", ["alembic_version"])
    
    # === RISCO ALTO (HIGH) ===
    
    # Detectar se toca tabela multi-tenant SEM filtro de tenant
    tenant_tables_touched = [t for t in tables if t in TENANT_TABLES]
    
    if tenant_tables_touched and not has_tenant_filter:
        # CRÍTICO: Acesso a dados multi-tenant sem isolamento!
        return ("HIGH", tenant_tables_touched)
    
    # === RISCO MÉDIO (MEDIUM) ===
    
    # 1. Tabelas whitelist (sistema, não precisam filtro)
    whitelist_tables_touched = [t for t in tables if t in WHITELIST_TABLES]
    if whitelist_tables_touched:
        return ("MEDIUM", whitelist_tables_touched)
    
    # 2. DDL statements (CREATE, ALTER, DROP)
    if any(pattern in sql_lower for pattern in [
        "create table",
        "alter table",
        "drop table",
        "create index",
        "drop index",
    ]):
        return ("MEDIUM", tables)
    
    # 3. Queries complexas com joins/CTEs (pode ser legítimo mas precisa revisão)
    if "with " in sql_lower or "cte" in sql_lower:
        return ("MEDIUM", tables)
    
    # 4. Nenhuma tabela detectada (pode ser subquery, função, etc.)
    if not tables:
        return ("MEDIUM", [])
    
    # === DEFAULT: RISCO MÉDIO ===
    # Se chegou aqui, não sabemos classificar com certeza
    return ("MEDIUM", tables)


def _increment_stats(
    risk_level: str,
    tables_detected: List[str],
    file_origin: str
) -> None:
    """
    Incrementa contadores de métricas em memória.
    
    Args:
        risk_level: HIGH, MEDIUM ou LOW
        tables_detected: Lista de tabelas detectadas
        file_origin: Arquivo de origem da query
    """
    # Incrementar total
    SQL_AUDIT_STATS["total"] += 1
    
    # Incrementar por risk level
    if risk_level in SQL_AUDIT_STATS:
        SQL_AUDIT_STATS[risk_level] += 1
    
    # Incrementar por arquivo
    if file_origin:
        if file_origin not in SQL_AUDIT_STATS["by_file"]:
            SQL_AUDIT_STATS["by_file"][file_origin] = 0
        SQL_AUDIT_STATS["by_file"][file_origin] += 1
    
    # Incrementar por tabela
    for table in tables_detected:
        if table not in SQL_AUDIT_STATS["by_table"]:
            SQL_AUDIT_STATS["by_table"][table] = 0
        SQL_AUDIT_STATS["by_table"][table] += 1


def _log_snapshot() -> None:
    """
    Loga snapshot das métricas acumuladas.
    
    Mostra:
    - Total de queries auditadas
    - Distribuição por risco (HIGH/MEDIUM/LOW)
    - Top 5 arquivos com mais queries
    - Top 5 tabelas mais acessadas
    """
    total = SQL_AUDIT_STATS["total"]
    
    if total == 0:
        return
    
    # Calcular percentuais
    high_pct = (SQL_AUDIT_STATS["HIGH"] / total * 100) if total > 0 else 0
    medium_pct = (SQL_AUDIT_STATS["MEDIUM"] / total * 100) if total > 0 else 0
    low_pct = (SQL_AUDIT_STATS["LOW"] / total * 100) if total > 0 else 0
    
    # Top 5 arquivos
    top_files = sorted(
        SQL_AUDIT_STATS["by_file"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Top 5 tabelas
    top_tables = sorted(
        SQL_AUDIT_STATS["by_table"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Atualizar timestamp
    SQL_AUDIT_STATS["last_snapshot"] = datetime.utcnow().isoformat()
    
    # Log estruturado
    logger.warning(
        "📊 SQL AUDIT SNAPSHOT",
        extra={
            "event": "sql_audit_snapshot",
            "timestamp": SQL_AUDIT_STATS["last_snapshot"],
            "total_queries": total,
            "high_count": SQL_AUDIT_STATS["HIGH"],
            "medium_count": SQL_AUDIT_STATS["MEDIUM"],
            "low_count": SQL_AUDIT_STATS["LOW"],
            "top_files": dict(top_files),
            "top_tables": dict(top_tables),
        }
    )
    
    # Log legível
    files_str = "\n    ".join([
        f"{i+1}. {file}: {count} queries"
        for i, (file, count) in enumerate(top_files)
    ]) if top_files else "none"
    
    tables_str = "\n    ".join([
        f"{i+1}. {table}: {count} accesses"
        for i, (table, count) in enumerate(top_tables)
    ]) if top_tables else "none"
    
    logger.warning(
        f"\n"
        f"{'='*80}\n"
        f"📊 SQL AUDIT SNAPSHOT - {total} queries audited\n"
        f"{'='*80}\n"
        f"📈 By Risk Level:\n"
        f"  🔴 HIGH:   {SQL_AUDIT_STATS['HIGH']:3d} ({high_pct:5.1f}%)\n"
        f"  🟡 MEDIUM: {SQL_AUDIT_STATS['MEDIUM']:3d} ({medium_pct:5.1f}%)\n"
        f"  🟢 LOW:    {SQL_AUDIT_STATS['LOW']:3d} ({low_pct:5.1f}%)\n"
        f"\n"
        f"📂 Top Files:\n"
        f"    {files_str}\n"
        f"\n"
        f"📊 Top Tables:\n"
        f"    {tables_str}\n"
        f"{'='*80}\n"
    )


def _is_raw_sql_text(statement: str) -> bool:
    """
    Verifica se o statement é RAW SQL (não é query ORM).
    
    ORM gera SQL como:
    - SELECT table.column FROM table WHERE ...
    - INSERT INTO table (col1, col2) VALUES (?, ?)
    
    RAW SQL tipicamente tem características como:
    - Espaçamento irregular
    - Comentários SQL
    - Funções complexas
    - CTEs (WITH ...)
    """
    if not statement:
        return False
    
    statement_lower = statement.lower().strip()
    
    # Indicadores de RAW SQL
    raw_sql_indicators = [
        "-- ",  # Comentários SQL
        "/* ",  # Comentários multi-linha
        "with ",  # CTEs
        "::text",  # Casting PostgreSQL
        "::jsonb",
        "coalesce(",
        "array_agg(",
        "string_agg(",
        "json_build_object(",
    ]
    
    for indicator in raw_sql_indicators:
        if indicator in statement_lower:
            return True
    
    return False


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
        if any(ignore in filename for ignore in [
            "sqlalchemy",
            "sql_audit.py",
            "contextlib.py",
            "threading.py",
        ]):
            continue
        
        # Pegar primeiro frame de código do usuário
        # Extrair apenas o nome do arquivo (sem path completo)
        file_short = filename.split("\\")[-1] if "\\" in filename else filename.split("/")[-1]
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


def _should_audit_statement(statement: str) -> bool:
    """
    Verifica se o statement deve ser auditado.
    
    Ignora:
    - Queries de migrations (alembic)
    - Queries de sistema (pg_catalog)
    - Queries de health check
    - Queries vazias
    
    Args:
        statement: SQL statement
        
    Returns:
        bool: True se deve auditar, False caso contrário
    """
    if not statement or len(statement.strip()) < 10:
        return False
    
    statement_lower = statement.lower()
    
    # Ignorar queries de sistema
    ignore_patterns = [
        "pg_catalog",
        "information_schema",
        "pg_stat_",
        "pg_class",
        "alembic_version",
        "select version()",
        "show server_version",
        "set time zone",
        "begin",
        "commit",
        "rollback",
        "savepoint",
    ]
    
    for pattern in ignore_patterns:
        if pattern in statement_lower:
            return False
    
    return True


@event.listens_for(Engine, "before_cursor_execute", retval=False)
def audit_raw_sql(
    conn: Connection,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool
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
        current_risk_index = risk_levels_order.index(risk_level) if risk_level in risk_levels_order else 0
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
            }
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
    risk_emoji = "🔴" if risk_level == "HIGH" else "🟡" if risk_level == "MEDIUM" else "🟢"
    
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
        }
    )
    
    # Log legível para console (desenvolvimento)
    tables_str = ", ".join(tables_detected) if tables_detected else "none"
    log_method(
        f"\n{'='*80}\n"
        f"{risk_emoji} RAW SQL OUTSIDE HELPER - RISK: {risk_level}\n"
        f"{'='*80}\n"
        f"📍 Origin: {file_origin}:{line_origin} in {func_origin}()\n"
        f"📊 Tables: {tables_str}\n"
        f"📝 SQL: {sql_truncated}\n"
        f"{'='*80}\n"
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
    # Adicionar status do listener
    stats = SQL_AUDIT_STATS.copy()
    stats["status"] = "active"
    stats["listener_registered"] = event.contains(Engine, "before_cursor_execute", audit_raw_sql)
    
    # Top 10 arquivos
    stats["top_files"] = sorted(
        SQL_AUDIT_STATS["by_file"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Top 10 tabelas
    stats["top_tables"] = sorted(
        SQL_AUDIT_STATS["by_table"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return stats


def reset_audit_stats() -> None:
    """
    Reseta todas as métricas (útil para testes).
    """
    SQL_AUDIT_STATS["total"] = 0
    SQL_AUDIT_STATS["HIGH"] = 0
    SQL_AUDIT_STATS["MEDIUM"] = 0
    SQL_AUDIT_STATS["LOW"] = 0
    SQL_AUDIT_STATS["by_file"] = {}
    SQL_AUDIT_STATS["by_table"] = {}
    SQL_AUDIT_STATS["last_snapshot"] = None
    logger.info("📊 SQL Audit stats reset")


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
        "blocks": f"{SQL_AUDIT_ENFORCE_LEVEL}+ risk queries" if SQL_AUDIT_ENFORCE else "none",
    }


# Auto-enable ao importar módulo
logger.info("🔍 SQL Audit module loaded - Hook registered")
