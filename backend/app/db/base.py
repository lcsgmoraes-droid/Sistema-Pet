from app.db.base_class import Base

# Importar TODOS os models aqui para o Alembic enxergar
# Importando models principais (do arquivo app/models.py)
from app.models import User, UserSession, Cliente, UserTenant, Pet, Especie, Raca  # noqa

# Importando models fiscais (do diretório app/fiscal_models/)
from app.fiscal_models import (  # noqa
    EmpresaConfigFiscal,
    FiscalCatalogoProdutos,
    FiscalEstadoPadrao,
    KitComposicao,
    KitConfigFiscal,
    ProdutoConfigFiscal,
)

# Importando produtos
from app.produtos_models import Produto, Marca, Categoria  # noqa

# Importando vendas
from app.vendas_models import Venda, VendaItem  # noqa

# Importando caixa
from app.caixa_models import Caixa  # noqa

# Importando outros models importantes para migrations
from app import conciliacao_models  # noqa
from app import financeiro_models  # noqa
from app import rotas_entrega_models  # noqa
from app import opportunities_models  # noqa
from app import opportunity_events_models  # noqa
from app import dre_plano_contas_models  # noqa
from app.ia import aba7_models  # noqa
# DESABILITADO TEMPORARIAMENTE: aba7_extrato_models tem dependências circulares
# from app.ia import aba7_extrato_models  # noqa

