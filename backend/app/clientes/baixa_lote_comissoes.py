"""Pós-commit idempotente apenas para os pagamentos do lote confirmado."""

import logging
from collections import defaultdict

from app.vendas_models import Venda, VendaBaixaLoteItem

logger = logging.getLogger(__name__)


def completar_comissoes_lote(db, lote):
    from app.vendas.comissoes import _gerar_comissoes_pendentes_venda

    if lote.status != "confirmado":
        return lote.resultado
    pagamentos_por_venda = defaultdict(set)
    for item in (
        db.query(VendaBaixaLoteItem)
        .filter_by(
            tenant_id=lote.tenant_id,
            lote_id=lote.id,
        )
        .all()
    ):
        pagamentos_por_venda[item.venda_id].add(item.pagamento_id)
    for venda_id, pagamento_ids in pagamentos_por_venda.items():
        venda = (
            db.query(Venda)
            .filter_by(
                id=venda_id,
                tenant_id=lote.tenant_id,
            )
            .first()
        )
        if not venda or not venda.funcionario_id:
            continue
        try:
            _gerar_comissoes_pendentes_venda(
                db=db,
                venda=venda,
                tenant_id=lote.tenant_id,
                trigger="baixa_vendas_lote",
                pagamento_ids=pagamento_ids,
            )
        except Exception:
            # A baixa já foi confirmada. Um reenvio retoma apenas esta comissão.
            db.rollback()
            logger.exception(
                "Comissão pendente na baixa em lote %s, venda %s", lote.id, venda_id
            )
    return lote.resultado
