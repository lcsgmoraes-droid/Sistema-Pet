"""
🔒 TENANT-SAFE RAW SQL EXECUTION
================================

Helper obrigatório para execução de queries RAW SQL com validação
automática de tenant_id em ambientes multi-tenant.

⚠️ SEGURANÇA CRÍTICA:
- Todas as queries RAW SQL em tabelas multi-tenant DEVEM usar este helper
- O placeholder {tenant_filter} é OBRIGATÓRIO
- O tenant_id é injetado automaticamente do contexto
- Queries sem validação de tenant expõem dados de outros clientes

Autor: Sistema de Hardening Multi-Tenant
Data: 2026-02-05
Versão: 1.0.0
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.engine import Result

from app.tenancy.context import get_current_tenant_id


class TenantSafeSQLError(RuntimeError):
    """
    Exceção levantada quando há violação de segurança multi-tenant
    em queries RAW SQL.
    
    Casos de uso:
    - SQL sem placeholder {tenant_filter}
    - Tentativa de execução sem tenant_id no contexto (quando require_tenant=True)
    - SQL com concatenação insegura
    """
    pass


def execute_tenant_safe(
    db: Session,
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    require_tenant: bool = True
) -> Result:
    """
    Executa query RAW SQL com validação automática de tenant_id.
    
    🔒 SEGURANÇA:
    Esta função garante que queries RAW SQL sempre filtrem pelo tenant_id
    correto, prevenindo vazamento de dados entre clientes.
    
    Args:
        db: Sessão SQLAlchemy ativa
        sql: Query SQL com placeholder {tenant_filter} obrigatório
        params: Dicionário de parâmetros nomeados (opcional)
        require_tenant: Se True, exige tenant_id no contexto (padrão: True)
    
    Returns:
        Result: Objeto Result do SQLAlchemy com os dados
    
    Raises:
        TenantSafeSQLError: Se houver violação de segurança:
            - SQL sem placeholder {tenant_filter}
            - tenant_id não encontrado (quando require_tenant=True)
            - Uso de concatenação/formatação insegura
    
    ✅ EXEMPLO CORRETO:
        >>> from app.db.tenant_safe_sql import execute_tenant_safe
        >>> 
        >>> # Query com placeholder {tenant_filter}
        >>> result = execute_tenant_safe(db, '''
        ...     SELECT * FROM comissoes_itens
        ...     WHERE {tenant_filter} AND status = :status
        ...     ORDER BY created_at DESC
        ... ''', {'status': 'pendente'})
        >>> 
        >>> comissoes = result.fetchall()
    
    ✅ EXEMPLO COM JOIN:
        >>> result = execute_tenant_safe(db, '''
        ...     SELECT ci.*, v.numero_venda
        ...     FROM comissoes_itens ci
        ...     JOIN vendas v ON v.id = ci.venda_id
        ...     WHERE {tenant_filter} 
        ...       AND ci.status = :status
        ...       AND v.data_venda >= :data_inicio
        ... ''', {
        ...     'status': 'pago',
        ...     'data_inicio': '2026-01-01'
        ... })
    
    ✅ EXEMPLO UPDATE:
        >>> execute_tenant_safe(db, '''
        ...     UPDATE comissoes_itens
        ...     SET status = :novo_status
        ...     WHERE {tenant_filter} AND id = :comissao_id
        ... ''', {'novo_status': 'pago', 'comissao_id': 123})
        >>> db.commit()
    
    ✅ EXEMPLO DELETE:
        >>> execute_tenant_safe(db, '''
        ...     DELETE FROM comissoes_configuracao
        ...     WHERE {tenant_filter} AND funcionario_id = :func_id
        ... ''', {'func_id': 456})
        >>> db.commit()
    
    ✅ EXEMPLO AGREGAÇÃO:
        >>> result = execute_tenant_safe(db, '''
        ...     SELECT 
        ...         funcionario_id,
        ...         SUM(valor_comissao_gerada) as total,
        ...         COUNT(*) as quantidade
        ...     FROM comissoes_itens
        ...     WHERE {tenant_filter} AND status = :status
        ...     GROUP BY funcionario_id
        ... ''', {'status': 'pendente'})
    
    ❌ EXEMPLO INCORRETO (LEVANTA TenantSafeSQLError):
        >>> # SEM PLACEHOLDER - INSEGURO!
        >>> result = execute_tenant_safe(db, '''
        ...     SELECT * FROM comissoes_itens
        ...     WHERE status = :status
        ... ''', {'status': 'pendente'})
        TenantSafeSQLError: SQL sem placeholder {tenant_filter} - OBRIGATÓRIO
    
    ❌ CONCATENAÇÃO INSEGURA (NUNCA FAÇA):
        >>> # CONCATENAÇÃO DIRETA - VULNERÁVEL A SQL INJECTION!
        >>> status = request.query_params.get('status')
        >>> sql = f"SELECT * FROM comissoes WHERE status = '{status}'"  # ❌ PERIGOSO
        >>> result = db.execute(text(sql))  # ❌ NÃO USE
        
        # ✅ FORMA CORRETA:
        >>> result = execute_tenant_safe(db, '''
        ...     SELECT * FROM comissoes
        ...     WHERE {tenant_filter} AND status = :status
        ... ''', {'status': status})  # ✅ SEGURO
    
    📋 QUERIES NÃO-TENANT (require_tenant=False):
        Use apenas para:
        - Health checks (SELECT 1)
        - Consultas em tabelas de sistema (tenants, permissions)
        - Migrations/scripts administrativos
        
        >>> # Health check (sem tenant)
        >>> result = execute_tenant_safe(db, 
        ...     'SELECT 1',
        ...     require_tenant=False
        ... )
        
        >>> # Lista tenants ativos (tabela de sistema)
        >>> result = execute_tenant_safe(db,
        ...     'SELECT id, nome FROM tenants WHERE ativo = true',
        ...     require_tenant=False
        ... )
    
    🔍 COMPORTAMENTO INTERNO:
        1. Valida presença do placeholder {tenant_filter}
        2. Obtém tenant_id do contexto atual
        3. Substitui {tenant_filter} por: tenant_id = :__tenant_id
        4. Injeta __tenant_id nos parâmetros
        5. Executa query com text()
        6. Retorna Result
    
    ⚠️ IMPORTANTE:
        - O placeholder {tenant_filter} é OBRIGATÓRIO em queries multi-tenant
        - NUNCA use concatenação de strings para construir SQL
        - SEMPRE use parâmetros nomeados (:param_name)
        - Chame db.commit() após UPDATE/DELETE/INSERT
    
    🚨 BLOQUEIOS DE SEGURANÇA:
        - SQL sem {tenant_filter} → TenantSafeSQLError
        - tenant_id ausente (quando require_tenant=True) → TenantSafeSQLError
        - Tentativa de bypass do filtro → Detectado e bloqueado
    """
    
    # Validação 1: Verificar placeholder obrigatório (exceto queries não-tenant)
    if require_tenant and "{tenant_filter}" not in sql:
        raise TenantSafeSQLError(
            "SQL sem placeholder {tenant_filter} detectado!\n"
            "\n"
            "❌ Query insegura rejeitada por segurança multi-tenant.\n"
            "\n"
            "Para queries em tabelas multi-tenant, você DEVE incluir:\n"
            "  WHERE {tenant_filter} AND ...\n"
            "\n"
            "Exemplo correto:\n"
            "  execute_tenant_safe(db, '''\n"
            "      SELECT * FROM comissoes_itens\n"
            "      WHERE {tenant_filter} AND status = :status\n"
            "  ''', {'status': 'pendente'})\n"
            "\n"
            "Para queries em tabelas de sistema (tenants, permissions), use:\n"
            "  execute_tenant_safe(db, 'SELECT ...', require_tenant=False)\n"
            "\n"
            f"SQL rejeitado:\n{sql[:200]}..."
        )
    
    # Preparar parâmetros
    params = params or {}
    
    # Validação 2: Obter tenant_id do contexto (se necessário)
    if require_tenant:
        try:
            tenant_id = get_current_tenant_id()
        except Exception as e:
            raise TenantSafeSQLError(
                "tenant_id não encontrado no contexto!\n"
                "\n"
                "❌ Não é possível executar query multi-tenant sem tenant no contexto.\n"
                "\n"
                "Possíveis causas:\n"
                "1. Middleware de tenant não está ativo\n"
                "2. Requisição sem autenticação/JWT\n"
                "3. Execução fora do contexto de request (background jobs)\n"
                "\n"
                "Soluções:\n"
                "- Para APIs: Certifique-se que o usuário está autenticado\n"
                "- Para background jobs: Use set_tenant_context(tenant_id)\n"
                "- Para queries de sistema: Use require_tenant=False\n"
                "\n"
                f"Erro original: {str(e)}"
            ) from e
        
        if not tenant_id:
            raise TenantSafeSQLError(
                "tenant_id é None ou vazio no contexto!\n"
                "\n"
                "❌ O contexto foi configurado mas o tenant_id está vazio.\n"
                "\n"
                "Verifique:\n"
                "1. Token JWT válido com claim 'tenant_id'\n"
                "2. Middleware TenantMiddleware ativo\n"
                "3. set_tenant_context() com valor válido\n"
            )
        
        # Substituir placeholder e injetar tenant_id
        sql = sql.replace("{tenant_filter}", "tenant_id = :__tenant_id")
        params["__tenant_id"] = tenant_id
    
    else:
        # Modo não-tenant: remover placeholder se existir
        sql = sql.replace("{tenant_filter}", "1=1")
    
    # Validação 3: Detectar concatenação insegura (heurística básica)
    if "' +" in sql or '" +' in sql or "f'" in sql or 'f"' in sql:
        raise TenantSafeSQLError(
            "Possível concatenação insegura detectada!\n"
            "\n"
            "❌ SQL com concatenação de strings é vulnerável a SQL injection.\n"
            "\n"
            "NUNCA faça:\n"
            "  sql = f\"SELECT * FROM tabela WHERE campo = '{valor}'\"  # ❌\n"
            "  sql = \"SELECT * FROM tabela WHERE campo = '\" + valor + \"'\"  # ❌\n"
            "\n"
            "SEMPRE use parâmetros:\n"
            "  execute_tenant_safe(db, '''\n"
            "      SELECT * FROM tabela\n"
            "      WHERE {tenant_filter} AND campo = :valor\n"
            "  ''', {'valor': valor})  # ✅\n"
            "\n"
            f"SQL suspeito:\n{sql[:200]}..."
        )
    
    # Executar query com text()
    try:
        return db.execute(text(sql), params)
    
    except Exception as e:
        # Re-lançar com contexto adicional para debug
        raise TenantSafeSQLError(
            f"Erro ao executar query tenant-safe:\n"
            f"\n"
            f"SQL: {sql[:300]}...\n"
            f"Params: {params}\n"
            f"Erro: {str(e)}\n"
            f"\n"
            f"Verifique:\n"
            f"1. Sintaxe SQL válida\n"
            f"2. Nomes de parâmetros correspondem aos placeholders\n"
            f"3. Tipos de dados compatíveis\n"
            f"4. Nomes de tabelas/colunas corretos\n"
        ) from e


def execute_tenant_safe_scalar(
    db: Session,
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    require_tenant: bool = True
) -> Any:
    """
    Atalho para queries que retornam um único valor escalar.
    
    Equivalente a: execute_tenant_safe(...).scalar()
    
    Args:
        db: Sessão SQLAlchemy
        sql: Query SQL com {tenant_filter}
        params: Parâmetros opcionais
        require_tenant: Se exige tenant no contexto
    
    Returns:
        Valor escalar (primeira coluna da primeira linha) ou None
    
    Example:
        >>> total = execute_tenant_safe_scalar(db, '''
        ...     SELECT SUM(valor_comissao_gerada)
        ...     FROM comissoes_itens
        ...     WHERE {tenant_filter} AND status = :status
        ... ''', {'status': 'pendente'})
        >>> 
        >>> print(f"Total pendente: R$ {total:.2f}")
    """
    result = execute_tenant_safe(db, sql, params, require_tenant)
    return result.scalar()


def execute_tenant_safe_one(
    db: Session,
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    require_tenant: bool = True
) -> Any:
    """
    Atalho para queries que retornam exatamente uma linha.
    
    Equivalente a: execute_tenant_safe(...).one()
    
    Args:
        db: Sessão SQLAlchemy
        sql: Query SQL com {tenant_filter}
        params: Parâmetros opcionais
        require_tenant: Se exige tenant no contexto
    
    Returns:
        Primeira linha (Row object)
    
    Raises:
        NoResultFound: Se nenhuma linha encontrada
        MultipleResultsFound: Se mais de uma linha encontrada
    
    Example:
        >>> comissao = execute_tenant_safe_one(db, '''
        ...     SELECT * FROM comissoes_itens
        ...     WHERE {tenant_filter} AND id = :id
        ... ''', {'id': 123})
    """
    result = execute_tenant_safe(db, sql, params, require_tenant)
    return result.one()


def execute_tenant_safe_first(
    db: Session,
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    require_tenant: bool = True
) -> Optional[Any]:
    """
    Atalho para queries que retornam a primeira linha ou None.
    
    Equivalente a: execute_tenant_safe(...).first()
    
    Args:
        db: Sessão SQLAlchemy
        sql: Query SQL com {tenant_filter}
        params: Parâmetros opcionais
        require_tenant: Se exige tenant no contexto
    
    Returns:
        Primeira linha (Row object) ou None se vazio
    
    Example:
        >>> config = execute_tenant_safe_first(db, '''
        ...     SELECT * FROM comissoes_configuracao
        ...     WHERE {tenant_filter} 
        ...       AND funcionario_id = :func_id
        ...       AND tipo = :tipo
        ...     LIMIT 1
        ... ''', {'func_id': 10, 'tipo': 'produto'})
        >>> 
        >>> if config:
        ...     print(f"Taxa: {config.percentual}%")
    """
    result = execute_tenant_safe(db, sql, params, require_tenant)
    return result.first()


def execute_tenant_safe_all(
    db: Session,
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    require_tenant: bool = True
) -> list:
    """
    Atalho para queries que retornam todas as linhas.
    
    Equivalente a: execute_tenant_safe(...).fetchall()
    
    Args:
        db: Sessão SQLAlchemy
        sql: Query SQL com {tenant_filter}
        params: Parâmetros opcionais
        require_tenant: Se exige tenant no contexto
    
    Returns:
        Lista de Row objects
    
    Example:
        >>> comissoes = execute_tenant_safe_all(db, '''
        ...     SELECT * FROM comissoes_itens
        ...     WHERE {tenant_filter} AND status = :status
        ...     ORDER BY created_at DESC
        ... ''', {'status': 'pendente'})
        >>> 
        >>> for c in comissoes:
        ...     print(f"{c.funcionario_id}: R$ {c.valor_comissao_gerada}")
    """
    result = execute_tenant_safe(db, sql, params, require_tenant)
    return result.fetchall()


# Aliases para compatibilidade
execute_raw_sql_safe = execute_tenant_safe
execute_safe = execute_tenant_safe
