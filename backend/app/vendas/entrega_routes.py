"""Rotas de status de entrega e retirada de vendas."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.services.order_push_notifications import notify_sale_order_event
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas.schemas import MarcarEntregueRequest
from app.vendas_models import Venda

router = APIRouter()


def _resolver_retirado_por_conclusao(venda, retirado_por: str | None) -> str | None:
    nome = str(retirado_por or "").strip()
    if not getattr(venda, "tem_entrega", False) and not nome:
        raise HTTPException(status_code=400, detail="Informe quem retirou o pedido.")
    return nome or None


@router.post("/{venda_id}/marcar-entregue")
async def marcar_venda_entregue(
    venda_id: int,
    dados: MarcarEntregueRequest = MarcarEntregueRequest(),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confirma que o cliente retirou o pedido na loja (ou terceiro apresentou a palavra-chave)."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    retirado_por = _resolver_retirado_por_conclusao(venda, dados.retirado_por)
    venda.status_entrega = "entregue"
    venda.data_entrega = datetime.now()
    if retirado_por:
        venda.retirado_por = retirado_por
    db.commit()
    notify_sale_order_event(db, venda=venda, event="delivered")
    return {
        "id": venda_id,
        "status_entrega": "entregue",
        "data_entrega": venda.data_entrega.isoformat(),
        "retirado_por": venda.retirado_por,
    }


@router.post("/{venda_id}/marcar-pronto-retirada")
async def marcar_venda_pronta_retirada(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Marca pedido de retirada/app/e-commerce como separado e pronto para o cliente."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")
    if venda.status_entrega == "entregue":
        raise HTTPException(status_code=400, detail="Venda ja foi entregue/retirada")
    venda.status_entrega = "pronto"
    db.commit()
    notify_sale_order_event(db, venda=venda, event="ready_for_pickup")
    return {"id": venda_id, "status_entrega": "pronto"}
