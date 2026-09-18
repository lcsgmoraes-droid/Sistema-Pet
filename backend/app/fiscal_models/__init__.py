"""
Models package - Fiscal models
Core models (User, Cliente) are in app/models.py file
"""

# Fiscal models (defined em outros módulos, reexportados aqui por compatibilidade)
# EmpresaConfigFiscal CONSOLIDADO no módulo canônico top-level
# (app/empresa_config_fiscal_models.py, BaseTenantModel/UUID — o que o runtime usa).
# A cópia divergente em fiscal_models/ (Integer tenant_id, sem Simples/trabalhista/CNAE)
# foi removida; reexportada aqui para os importadores de app.fiscal_models.
from app.empresa_config_fiscal_models import EmpresaConfigFiscal  # noqa

# FiscalCatalogoProdutos e FiscalEstadoPadrao foram CONSOLIDADOS nos módulos canônicos
# top-level (app/fiscal_catalogo_produtos_models.py e app/fiscal_estado_padrao_models.py),
# que são os mesmos importados pelos serviços de runtime. As cópias divergentes que
# existiam aqui em fiscal_models/ mapeavam o mesmo __tablename__ no mesmo registry
# SQLAlchemy — se ambos os módulos fossem importados no mesmo processo, o registro da
# segunda classe lançava sqlalchemy.exc.InvalidRequestError (Table already defined).
# Removidas; reexportadas aqui para manter compatibilidade com db/base.py e demais
# importadores de app.fiscal_models.
from app.fiscal_catalogo_produtos_models import FiscalCatalogoProdutos  # noqa
from app.fiscal_estado_padrao_models import FiscalEstadoPadrao  # noqa
from .kit_composicao import KitComposicao  # noqa

# KitConfigFiscal e ProdutoConfigFiscal foram CONSOLIDADOS nos módulos canônicos
# top-level (app/kit_config_fiscal_models.py e app/produto_config_fiscal_models.py),
# que são os mesmos importados pelos serviços de runtime. Reexportados aqui para
# manter compatibilidade com db/base.py e demais importadores de app.fiscal_models.
from app.kit_config_fiscal_models import KitConfigFiscal  # noqa
from app.produto_config_fiscal_models import ProdutoConfigFiscal  # noqa

__all__ = [
    "EmpresaConfigFiscal",
    "FiscalCatalogoProdutos",
    "FiscalEstadoPadrao",
    "KitComposicao",
    "KitConfigFiscal",
    "ProdutoConfigFiscal",
]
