from app.db.base_class import Base

__all__ = ["Base"]

# Importar TODOS os models aqui para o Alembic enxergar
# Importando models principais (do arquivo app/models.py)
from app.models import User, UserSession, Cliente, UserTenant, Pet, Especie, Raca  # noqa
from app.campaigns.cashback_crm_models import CashbackContato  # noqa: F401

# Importando models fiscais (do diretório app/fiscal_models/)
# KitConfigFiscal/ProdutoConfigFiscal são reexportados de app.fiscal_models a partir
# dos módulos canônicos top-level (consolidação).
from app.fiscal_models import (  # noqa
    EmpresaConfigFiscal,
    FiscalCatalogoProdutos,
    FiscalEstadoPadrao,
    KitConfigFiscal,
    ProdutoConfigFiscal,
)

# variacao_config_fiscal não tem cópia em fiscal_models/: importar o módulo canônico
# direto para registrar a tabela no metadata do Alembic.
from app.variacao_config_fiscal_models import VariacaoConfigFiscal  # noqa

# Espécie/Raça mestre (camada geral do grupo comercial, Checkpoint 1) —
# módulo próprio, não reexportado por app.models.
from app.especie_raca_mestre_models import EspecieMestre, RacaMestre  # noqa

# Importando produtos
from app.produtos_models import Produto, Marca, Categoria  # noqa
from app.produto_identity_models import ProdutoSkuAlias, ProdutoFusaoLog  # noqa

# Identidade de produto compartilhada entre lojas do grupo comercial (fase D,
# substitui o ProdutoMestre) — ver app/produto_identidade_models.py.
from app.produto_identidade_models import (  # noqa
    ProdutoIdentidade,
    ProdutoIdentidadeBackfillRun,
    ProdutoIdentidadeConflito,
    ProdutoIdentidadeHistoricoAlteracao,
)

# Importando vendas
from app.vendas_models import Venda, VendaItem  # noqa

# Importando caixa
from app.caixa_models import Caixa  # noqa

# Importando outros models importantes para migrations
from app import conciliacao_models  # noqa
from app import financeiro_models  # noqa
from app.financeiro import models_imobilizado  # noqa
from app.financeiro import models_valor_empresa  # noqa
from app import funcionario_contagem_models  # noqa
from app import rotas_entrega_models  # noqa
from app import opportunities_models  # noqa
from app import opportunity_events_models  # noqa
from app import ecommerce_analytics_models  # noqa
from app import dre_plano_contas_models  # noqa
from app import nfe_cache_models  # noqa
from app import xml_contabilidade_models  # noqa: F401
from app import compras_pendencias_models  # noqa
from app import bling_pedido_webhook_queue_models  # noqa
from app import catalogo_mestre_models  # noqa
from app.ia import aba7_models  # noqa
# DESABILITADO TEMPORARIAMENTE: aba7_extrato_models tem dependências circulares
# from app.ia import aba7_extrato_models  # noqa
