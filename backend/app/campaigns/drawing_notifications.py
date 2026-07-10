"""Helpers de notificacao para sorteios de campanhas."""

from app.campaigns.app_push import enqueue_campaign_push


def enqueue_drawing_winner_push(db, *, tenant_id, drawing, cliente) -> bool:
    if not cliente:
        return False

    prize_text = drawing.prize_description or "o premio"
    return enqueue_campaign_push(
        db,
        tenant_id=tenant_id,
        customer_id=cliente.id,
        title=f"Voce ganhou o sorteio: {drawing.name}",
        body=(
            f"Parabens, {cliente.nome}! Voce foi sorteado(a) no sorteio "
            f"{drawing.name}. Premio: {prize_text}."
        ),
        idempotency_key=f"sorteio:{drawing.id}:ganhador:{cliente.id}:push",
        kind="drawing_winner",
        payload={
            "target": "benefits",
            "campaign_type": "drawing",
            "drawing_id": drawing.id,
            "drawing_name": drawing.name,
            "customer_id": cliente.id,
            "prize": prize_text,
        },
    )
