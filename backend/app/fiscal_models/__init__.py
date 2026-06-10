"""
Models package - Fiscal models
Core models (User, Cliente) are in app/models.py file
"""

# Fiscal models (defined in this directory)
# EmpresaConfigFiscal CONSOLIDADO no módulo canônico top-level
# (app/empresa_config_fiscal_models.py, BaseTenantModel/UUID — o que o runtime usa).
# A cópia divergente em fiscal_models/ (Integer tenant_id, sem Simples/trabalhista/CNAE)
# foi removida; reexportada aqui para os importadores de app.fiscal_models.
from app.empresa_config_fiscal_models import EmpresaConfigFiscal  # noqa
from .fiscal_catalogo_produtos import FiscalCatalogoProdutos  # noqa
from .fiscal_estado_padrao import FiscalEstadoPadrao  # noqa
from .kit_composicao import KitComposicao  # noqa

# KitConfigFiscal e ProdutoConfigFiscal foram CONSOLIDADOS nos módulos canônicos
# top-level (app/kit_config_fiscal_models.py e app/produto_config_fiscal_models.py),
# que são os mesmos importados pelos serviços de runtime. Reexportados aqui para
# manter compatibilidade com db/base.py e demais importadores de app.fiscal_models.
from app.kit_config_fiscal_models import KitConfigFiscal  # noqa
from app.produto_config_fiscal_models import ProdutoConfigFiscal  # noqa

__all__ = [
    'EmpresaConfigFiscal',
    'FiscalCatalogoProdutos',
    'FiscalEstadoPadrao',
    'KitComposicao',
    'KitConfigFiscal',
    'ProdutoConfigFiscal',
]
