"""
ORM Tenant Filters with Fail-Fast (Phase 1.3)
==============================================

RESPONSABILIDADE:
- Injetar WHERE tenant_id = ? automaticamente em queries de BaseTenantModel
- FAIL-FAST: Rejeitar queries sem tenant_id em tabelas multi-tenant
- Permitir apenas whitelist de tabelas sem tenant

WHITELIST:
- Tabelas de autenticação e controle de acesso
- Tabelas que NÃO herdam de BaseTenantModel naturalmente (Tenant, Permission, UserSession)
"""

from sqlalchemy.orm import Session
from sqlalchemy import event, inspect
from sqlalchemy.orm import with_loader_criteria
import logging

from app.tenancy.context import get_current_tenant
from app.base_models import BaseTenantModel


logger = logging.getLogger(__name__)

# WHITELIST: Tabelas que podem ser acessadas sem tenant_id no contexto
# Critério de inclusão:
# 1. Tabelas de autenticação (users, user_sessions)
# 2. Tabelas de controle de acesso (tenants, user_tenants, roles, permissions, role_permissions)
# 3. Tabelas de auditoria que precisam registrar eventos sem tenant (audit_logs)
TENANT_WHITELIST_TABLES = {
    'users',           # Necessário para login (antes de selecionar tenant)
    'tenants',         # Necessário para listar tenants disponíveis
    'user_sessions',   # Sessões não são tenant-specific
    'user_tenants',    # Necessário para /auth/select-tenant
    'roles',           # Necessário para carregar permissões
    'permissions',     # Permissões globais do sistema
    'role_permissions',# Necessário para carregar permissões
    'audit_logs',      # Pode precisar registrar eventos sem tenant
}


def _get_query_primary_table(execute_state):
    """
    Extrai a tabela principal de uma query SQLAlchemy.
    
    Returns:
        str | None: Nome da tabela ou None se não for possível determinar
    """
    try:
        # Tentar obter do statement context
        if hasattr(execute_state, 'statement'):
            statement = execute_state.statement
            
            # Queries ORM têm column_descriptions
            if hasattr(statement, 'column_descriptions') and statement.column_descriptions:
                entity = statement.column_descriptions[0].get('entity')
                if entity:
                    return entity.__tablename__
            
            # Tentar via froms
            if hasattr(statement, 'froms') and statement.froms:
                for from_clause in statement.froms:
                    if hasattr(from_clause, 'name'):
                        return from_clause.name
        
        return None
    except Exception as e:
        logger.warning(f"[ORM FAIL-FAST] Não foi possível determinar tabela da query: {e}")
        return None


@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    """
    Filtro global automático de tenant com FAIL-FAST.
    
    Comportamento (Phase 1.3):
    1. Se não for SELECT, permite (INSERT/UPDATE/DELETE passam)
    2. Obtém tenant_id do contexto
    3. Se tenant_id PRESENTE:
       - Injeta WHERE tenant_id = ? automaticamente
    4. Se tenant_id AUSENTE:
       - Determina tabela principal da query
       - Se tabela na WHITELIST: permite
       - Se tabela herda de BaseTenantModel: FAIL-FAST (RuntimeError)
       - Se não conseguir determinar tabela: FAIL-FAST por segurança
    
    Raises:
        RuntimeError: Query em tabela multi-tenant sem tenant_id no contexto
    """
    # Permitir operações que não são SELECT (INSERT, UPDATE, DELETE)
    if not execute_state.is_select:
        return

    tenant_id = get_current_tenant()
    
    if tenant_id is not None:
        # CASO 1: Tenant presente → aplicar filtro normalmente
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                BaseTenantModel,
                lambda cls: cls.tenant_id == tenant_id,
                include_aliases=True,
            )
        )
        return
    
    # CASO 2: Tenant ausente → validar se é permitido
    
    # Tentar determinar a tabela principal
    table_name = _get_query_primary_table(execute_state)
    
    if table_name:
        # Se tabela está na whitelist, permitir
        if table_name in TENANT_WHITELIST_TABLES:
            logger.debug(f"[ORM FAIL-FAST] Query em tabela whitelist permitida: {table_name}")
            return
        
        # Se tabela não está na whitelist, verificar se herda de BaseTenantModel
        # Percorrer todas as classes mapeadas para encontrar a tabela
        from sqlalchemy.orm import class_mapper
        from app.db import Base
        
        for mapper in Base.registry.mappers:
            mapped_class = mapper.class_
            if hasattr(mapped_class, '__tablename__') and mapped_class.__tablename__ == table_name:
                # Verificar se herda de BaseTenantModel
                if issubclass(mapped_class, BaseTenantModel):
                    # FAIL-FAST: Tabela multi-tenant sem tenant_id
                    error_msg = (
                        f"[ORM FAIL-FAST] Tentativa de query em tabela multi-tenant '{table_name}' "
                        f"sem tenant_id no contexto. "
                        f"Use get_current_user_and_tenant() na rota ou adicione a tabela à whitelist "
                        f"se for realmente necessário acessá-la sem tenant."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                else:
                    # Tabela não herda de BaseTenantModel, permitir
                    logger.debug(f"[ORM FAIL-FAST] Query em tabela não-tenant permitida: {table_name}")
                    return
    
    # CASO 3: Não foi possível determinar a tabela
    # Por segurança, FAIL-FAST (melhor falhar do que vazar dados)
    error_msg = (
        f"[ORM FAIL-FAST] Não foi possível determinar a tabela da query e tenant_id está ausente. "
        f"Por segurança, a query foi bloqueada. "
        f"Certifique-se de usar get_current_user_and_tenant() em rotas multi-tenant."
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)

