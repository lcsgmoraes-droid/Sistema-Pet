"""Fachada compat?vel dos servi?os de concilia??o.

As implementa??es foram separadas por fluxo para manter este m?dulo est?vel
para imports legados usados pelas rotas.
"""

from .conciliacao_services_importacao import (
    importar_arquivo_operadora,
    processar_conciliacao,
    reverter_conciliacao,
    validar_importacao_cascata,
)
from .conciliacao_services_recebimentos import (
    amarrar_recebimentos_vendas,
    validar_recebimentos_cascata_v2,
)
from .conciliacao_services_stone import (
    conciliar_vendas_stone,
    processar_upload_conciliacao_vendas,
)

__all__ = [
    "amarrar_recebimentos_vendas",
    "conciliar_vendas_stone",
    "importar_arquivo_operadora",
    "processar_conciliacao",
    "processar_upload_conciliacao_vendas",
    "reverter_conciliacao",
    "validar_importacao_cascata",
    "validar_recebimentos_cascata_v2",
]
