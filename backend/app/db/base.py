from app.db.base_class import Base

# Importar TODOS os models aqui para o Alembic enxergar
# Importando models principais (do arquivo app/models.py)
from app.models import User, UserSession, Cliente, UserTenant  # noqa

# Importando models fiscais (do diretório app/models/)
from app.models import (  # noqa
    EmpresaConfigFiscal,
    FiscalCatalogoProdutos,
    FiscalEstadoPadrao,
    KitComposicao,
    KitConfigFiscal,
    ProdutoConfigFiscal,
)

# Importando outros models importantes para migrations
from app import produtos_models  # noqa
from app import financeiro_models  # noqa
from app import rotas_entrega_models  # noqa
from app import opportunities_models  # noqa
from app import opportunity_events_models  # noqa
from app import dre_plano_contas_models  # noqa
from app.ia import aba7_models, aba7_extrato_models  # noqa
