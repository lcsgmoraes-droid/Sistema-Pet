"""
Models package - Exports all models from app.models module
This allows imports like: from app.models import User, Cliente
"""

# Import all models from the main models.py file
import sys
from pathlib import Path

# Import from parent models.py file
from app.models import (
    User,
    UserSession,
    Cliente,
    UserTenant,
    # Add other commonly used models here as needed
)

# Make sure the fiscal models are accessible
from .empresa_config_fiscal import *  # noqa
from .fiscal_catalogo_produtos import *  # noqa
from .fiscal_estado_padrao import *  # noqa
from .kit_composicao import *  # noqa
from .kit_config_fiscal import *  # noqa
from .produto_config_fiscal import *  # noqa

__all__ = [
    'User',
    'UserSession',
    'Cliente',
    'UserTenant',
]
