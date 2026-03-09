"""Rotas Admin — Drive pickup: PDV acompanha clientes que chegaram no estacionamento."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.pedido_models import Pedido
from app.utils.timezone import now_brasilia

router = APIRouter(prefix="/ecommerce-drive", tags=["ecommerce-drive"])


@router.get("/aguardando")
def listar_drive_aguardando(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    PDV usa este endpoint para ver clientes que pressionaram 'Cheguei'.
    Retorna pedidos com drive_chegou_at preenchido e drive_entregue_at vazio.
    """
    _, tenant_id = user_and_tenant
    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == str(tenant_id),
            Pedido.is_drive == True,
            Pedido.drive_chegou_at.isnot(None),
            Pedido.drive_entregue_at.is_(None),
        )
        .order_by(Pedido.drive_chegou_at.asc())
        .all()
    )

    return {
        "total": len(pedidos),
        "pedidos": [
            {
                "pedido_id": p.pedido_id,
                "cliente_id": p.cliente_id,
                "total": float(p.total or 0.0),
                "palavra_chave_retirada": p.palavra_chave_retirada,
                "drive_chegou_at": p.drive_chegou_at.isoformat() if p.drive_chegou_at else None,
                "status": p.status,
            }
            for p in pedidos
        ],
    }


@router.post("/pedido/{pedido_id}/entregue")
def confirmar_drive_entregue(
    pedido_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Funcionário da loja confirma que entregou o pedido no drive."""
    _, tenant_id = user_and_tenant
    pedido = (
        db.query(Pedido)
        .filter(
            Pedido.pedido_id == pedido_id,
            Pedido.tenant_id == str(tenant_id),
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

    if not pedido.is_drive:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este pedido não é drive")

    if pedido.drive_entregue_at:
        return {
            "pedido_id": pedido.pedido_id,
            "drive_entregue_at": pedido.drive_entregue_at.isoformat(),
            "message": "Entrega já confirmada anteriormente",
        }

    pedido.drive_entregue_at = now_brasilia()
    db.commit()

    return {
        "pedido_id": pedido.pedido_id,
        "drive_entregue_at": pedido.drive_entregue_at.isoformat(),
        "message": "Entrega no drive confirmada com sucesso!",
    }
