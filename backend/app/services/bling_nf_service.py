from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.estoque_reserva_service import EstoqueReservaService
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.utils.logger import logger


def buscar_produto_do_item(db: Session, tenant_id, sku: str):
    from app.produtos_models import Produto

    if not sku:
        return None

    return (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(Produto.codigo == sku, Produto.codigo_barras == sku),
        )
        .first()
    )


def processar_nf_autorizada(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str,
) -> str:
    if pedido.status == "confirmado" and all(item.vendido_em for item in itens):
        return "venda_ja_confirmada"

    pedido.status = "confirmado"
    pedido.confirmado_em = datetime.now(timezone.utc)

    for item in itens:
        if item.vendido_em:
            continue

        EstoqueReservaService.confirmar_venda(db, item)

        try:
            from app.estoque.service import EstoqueService

            produto = buscar_produto_do_item(
                db=db,
                tenant_id=pedido.tenant_id,
                sku=item.sku,
            )

            if produto:
                EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=float(item.quantidade),
                    motivo="venda_bling",
                    referencia_id=pedido.id,
                    referencia_tipo="pedido_integrado",
                    user_id=0,
                    db=db,
                    tenant_id=pedido.tenant_id,
                    documento=pedido.pedido_bling_numero,
                    observacao=f"Baixa automática via NF Bling #{nf_id}",
                )
            else:
                logger.warning(f"⚠️  Produto com código/SKU '{item.sku}' não encontrado para baixa de estoque")

        except Exception as e:
            logger.warning(f"⚠️  Falha ao baixar estoque para SKU {item.sku}: {e}")

    db.add(pedido)
    db.commit()
    return "venda_confirmada"


def processar_nf_cancelada(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
) -> str:
    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.now(timezone.utc)

    for item in itens:
        EstoqueReservaService.liberar(db, item)

    db.add(pedido)
    db.commit()
    return "venda_cancelada"