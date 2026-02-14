"""
Models package - Registry of all application models
"""

# Import core models from app.models.py (the file, not this directory)
# Using absolute import to avoid confusion with this directory
import sys
import os

# These models are defined in backend/app/models.py (the file)
try:
    from ..models import User, UserSession, Cliente, UserTenant
except ImportError:
    # Fallback for when imported from outside
    import app.models as models_module
    User = models_module.User
    UserSession = models_module.UserSession
    Cliente = models_module.Cliente
    UserTenant = models_module.UserTenant

# Fiscal models (defined in this directory)
from .empresa_config_fiscal import EmpresaConfigFiscal  # noqa
from .fiscal_catalogo_produtos import FiscalCatalogoProdutos  # noqa
from .fiscal_estado_padrao import FiscalEstadoPadrao  # noqa
from .kit_composicao import KitComposicao  # noqa
from .kit_config_fiscal import KitConfigFiscal  # noqa
from .produto_config_fiscal import ProdutoConfigFiscal  # noqa

__all__ = [
    'User',
    'UserSession',
    'Cliente',
    'UserTenant',
    'EmpresaConfigFiscal',
    'FiscalCatalogoProdutos',
    'FiscalEstadoPadrao',
    'KitComposicao',
    'KitConfigFiscal',
    'ProdutoConfigFiscal',
]
