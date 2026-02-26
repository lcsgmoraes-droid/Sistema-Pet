from app.db.session import SessionLocal
from app.read_models.pedido_checkout_read import PedidoCheckoutRead


def projetar_pedido_checkout(event):
    """
    Projection handler SAFE.
    Não interfere em ERP.
    """

    db = SessionLocal()

    try:
        db.add(
            PedidoCheckoutRead(
                pedido_id=event.pedido_id,
                cliente_id=event.cliente_id,
                tenant_id=event.tenant_id,
                total=event.total,
                items_count=getattr(event, "items_count", 0),
                subtotal_items=getattr(event, "subtotal_items", 0.0),
                origem=event.origem,
            )
        )
        db.commit()
    finally:
        db.close()