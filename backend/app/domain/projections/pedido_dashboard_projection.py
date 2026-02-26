from sqlalchemy.orm import Session
from app.domain.read_models.pedido_dashboard_read import PedidoDashboardRead
from datetime import datetime
from app.domain.events.read_model_events import ReadModelUpdatedEvent
from app.domain.events.event_observability import log_event

def projetar_pedido_dashboard(event, db: Session):
    row = db.query(PedidoDashboardRead).first()

    if not row:
        row = PedidoDashboardRead(
            total_pedidos=0,
            total_vendas=0,
            total_itens=0,
            ticket_medio=0
        )
        db.add(row)
        db.flush()

    total = float(getattr(event, "total", 0) or 0)
    itens = int(getattr(event, "items_count", 0) or 0)

    row.total_pedidos += 1
    row.total_vendas += total
    row.total_itens += itens

    if row.total_pedidos > 0:
        row.ticket_medio = row.total_vendas / row.total_pedidos

    db.commit()

    log_event(
        stage="projection",
        event="PedidoCriadoEvent",
        source="pedido_dashboard_projection"
    )

    # internal signal (phase 13)
    event_signal = ReadModelUpdatedEvent(
        model="pedido_dashboard_read",
        occurred_at=datetime.utcnow()
    )

    # somente debug/runtime visibility por enquanto
    print(f"[READ_MODEL_UPDATED] {event_signal}")

