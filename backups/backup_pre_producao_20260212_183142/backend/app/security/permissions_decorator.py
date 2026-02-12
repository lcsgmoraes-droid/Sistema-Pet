from functools import wraps
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from inspect import signature
import asyncio
from uuid import UUID

from app.db import get_session as get_db
from app.auth import get_current_user
from app.security.permissions_service import check_permission


def require_permission(permission: str):
    """
    Decorator para verificar permissões em rotas FastAPI.
    A função decorada deve ter parâmetros 'db' e ('current_user' ou 'user_and_tenant').
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Tenta obter db e user dos kwargs
            db: Session = kwargs.get('db')
            current_user = kwargs.get('current_user')
            user_and_tenant = kwargs.get('user_and_tenant')
            tenant_id: UUID = None
            
            # Se user_and_tenant existe, extrai o current_user e tenant_id dele
            if user_and_tenant and isinstance(user_and_tenant, tuple):
                current_user = user_and_tenant[0]
                tenant_id = user_and_tenant[1] if len(user_and_tenant) > 1 else None
            
            # Verifica se temos os parâmetros necessários
            if db is None or current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Configuração de permissão inválida: db e current_user são obrigatórios"
                )
            
            # Verifica a permissão (passa tenant_id se disponível)
            try:
                check_permission(db, current_user.id, permission, tenant_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Erro ao verificar permissão: {str(e)}"
                )
            
            # Chama a função original
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Tenta obter db e user dos kwargs
            db: Session = kwargs.get('db')
            current_user = kwargs.get('current_user')
            user_and_tenant = kwargs.get('user_and_tenant')
            tenant_id: UUID = None
            
            # Se user_and_tenant existe, extrai o current_user e tenant_id dele
            if user_and_tenant and isinstance(user_and_tenant, tuple):
                current_user = user_and_tenant[0]
                tenant_id = user_and_tenant[1] if len(user_and_tenant) > 1 else None
            
            # Verifica se temos os parâmetros necessários
            if db is None or current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Configuração de permissão inválida: db e current_user são obrigatórios"
                )
            
            # Verifica a permissão (passa tenant_id se disponível)
            try:
                check_permission(db, current_user.id, permission, tenant_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Erro ao verificar permissão: {str(e)}"
                )
            
            # Chama a função original
            return func(*args, **kwargs)
        
        # Retorna o wrapper apropriado baseado se a função é async ou não
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
