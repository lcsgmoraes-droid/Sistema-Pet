"""
Módulo de Autenticação
=======================

Dependências e helpers para autenticação e autorização.
"""

# Importar funções core
from .core import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_user_from_token,
    get_current_active_superuser
)

# Importar dependências locais
from .dependencies import require_admin, require_active_user, get_current_user_and_tenant

__all__ = [
    'hash_password',
    'verify_password',
    'create_access_token',
    'get_current_user',
    'get_current_user_from_token',
    'get_current_active_superuser',
    'require_admin',
    'require_active_user',
    'get_current_user_and_tenant'
]
