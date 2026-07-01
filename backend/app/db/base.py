from app.db.base_class import Base

__all__ = ["Base"]

# Importar TODOS os models aqui para o Alembic enxergar
# Importando models principais (do arquivo app/models.py)
from app.models import User, UserSession, Cliente, UserTenant, Pet, Especie, Raca  # noqa

# Importando models fiscais (do diretório app/fiscal_models/)
# KitConfigFiscal/ProdutoConfigFiscal são reexportados de app.fiscal_models a partir
# dos módulos canônicos top-level (consolidação).
from app.fiscal_models import (  # noqa
    EmpresaConfigFiscal,
    FiscalCatalogoProdutos,
    FiscalEstadoPadrao,
    KitComposicao,
    KitConfigFiscal,
    ProdutoConfigFiscal,
)

# variacao_config_fiscal não tem cópia em fiscal_models/: importar o módulo canônico
# direto para registrar a tabela no metadata do Alembic.
from app.variacao_config_fiscal_models import VariacaoConfigFiscal  # noqa

# Importando produtos
from app.produtos_models import Produto, Marca, Categoria  # noqa

# Importando vendas
from app.vendas_models import Venda, VendaItem  # noqa

# Importando caixa
from app.caixa_models import Caixa  # noqa

# Importando outros models importantes para migrations
from app import conciliacao_models  # noqa
from app import financeiro_models  # noqa
from app import funcionario_contagem_models  # noqa
from app import rotas_entrega_models  # noqa
from app import opportunities_models  # noqa
from app import opportunity_events_models  # noqa
from app import dre_plano_contas_models  # noqa
from app import nfe_cache_models  # noqa
from app import compras_pendencias_models  # noqa
from app import bling_pedido_webhook_queue_models  # noqa
from app.ia import aba7_models  # noqa
# DESABILITADO TEMPORARIAMENTE: aba7_extrato_models tem dependências circulares
# from app.ia import aba7_extrato_models  # noqa
