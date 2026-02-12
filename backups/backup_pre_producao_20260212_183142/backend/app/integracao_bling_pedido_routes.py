
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.session import get_db
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - Pedido"]
)

@router.post("/pedido")
async def receber_pedido_bling(request: Request, db: Session = next(get_db())):
    payload = await request.json()

    pedido_id = str(payload.get("id"))
    numero = payload.get("numero")
    canal = payload.get("origem", "online")
    itens = payload.get("itens", [])

    if not pedido_id:
        raise HTTPException(status_code=400, detail="Pedido sem ID")

    # Idempotência
    existente = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.pedido_bling_id == pedido_id
    ).first()

    if existente:
        return {"status": "ignorado", "motivo": "pedido_ja_existe"}

    pedido = PedidoIntegrado(
        pedido_bling_id=pedido_id,
        pedido_bling_numero=numero,
        canal=canal,
        status="aberto",
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload=payload
    )

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    for item in itens:
        sku = item.get("sku")
        descricao = item.get("descricao")
        quantidade = int(item.get("quantidade", 0))

        if not sku or quantidade <= 0:
            continue

        item_pedido = PedidoIntegradoItem(
            pedido_integrado_id=pedido.id,
            sku=sku,
            descricao=descricao,
            quantidade=quantidade
        )

        # Reserva de estoque
        EstoqueReservaService.reservar(db, item_pedido)

        db.add(item_pedido)

    db.commit()

    return {"status": "ok", "pedido_id": pedido.id}
