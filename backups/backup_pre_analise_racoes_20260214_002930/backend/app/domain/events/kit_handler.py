"""
KitEstoqueEventHandler
Recalcula estoque virtual de KITs quando produtos componentes
sofrem impacto por venda ou cancelamento.
"""

import logging
from sqlalchemy.orm import Session

from app.domain.events.venda_events import VendaFinalizada, VendaCancelada
from app.services.kit_estoque_service import KitEstoqueService
from app.vendas_models import Venda, VendaItem
from app.db import get_session

logger = logging.getLogger(__name__)


class KitEstoqueEventHandler:
    """
    Handler responsável por manter o estoque virtual de KITs consistente.
    """

    @staticmethod
    def _recalcular_kits_por_venda(db: Session, venda_id: int) -> None:
        """
        Busca os produtos da venda e recalcula todos os KITs
        que utilizam esses produtos como componentes.
        """
        itens = (
            db.query(VendaItem)
            .filter(VendaItem.venda_id == venda_id)
            .all()
        )

        produtos_afetados = {item.produto_id for item in itens}

        for produto_id in produtos_afetados:
            kits_recalculados = KitEstoqueService.recalcular_kits_que_usam_produto(
                db=db,
                produto_id=produto_id
            )

            logger.info(
                f"♻️ KIT | Produto {produto_id} afetou "
                f"{len(kits_recalculados)} KIT(s)"
            )

    @staticmethod
    def on_venda_finalizada(event: VendaFinalizada) -> None:
        """
        Disparado após finalização de venda.
        O estoque já foi baixado neste ponto.
        """
        try:
            db = next(get_session())
            KitEstoqueEventHandler._recalcular_kits_por_venda(
                db=db,
                venda_id=event.venda_id
            )
        except Exception as e:
            logger.error(
                f"❌ Erro ao recalcular KITs após venda finalizada: {e}",
                exc_info=True
            )

    @staticmethod
    def on_venda_cancelada(event: VendaCancelada) -> None:
        """
        Disparado após cancelamento de venda.
        O estoque já foi estornado neste ponto.
        """
        try:
            db = next(get_session())
            KitEstoqueEventHandler._recalcular_kits_por_venda(
                db=db,
                venda_id=event.venda_id
            )
        except Exception as e:
            logger.error(
                f"❌ Erro ao recalcular KITs após cancelamento de venda: {e}",
                exc_info=True
            )
