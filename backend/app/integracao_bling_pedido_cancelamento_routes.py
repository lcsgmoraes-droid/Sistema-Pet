from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_flow_monitor_models import BlingFlowIncident
from app.db import get_session
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.services.pedido_cancelamento_fiscal_estoque_service import (
    INCIDENTE_RETORNO_ESTOQUE_PENDENTE,
    decidir_retorno_estoque,
    solicitar_cancelamento_nf_bling,
)
from app.utils.logger import logger


router = APIRouter()


class SolicitarCancelamentoNFRequest(BaseModel):
    justificativa: Optional[str] = None


class DecisaoRetornoEstoqueRequest(BaseModel):
    acao: str
    motivo: str


def _buscar_pedido_com_itens(
    db: Session,
    *,
    tenant_id,
    pedido_id: int,
) -> tuple[PedidoIntegrado, list[PedidoIntegradoItem]]:
    pedido = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.id == pedido_id,
            PedidoIntegrado.tenant_id == tenant_id,
        )
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(
            PedidoIntegradoItem.tenant_id == tenant_id,
            PedidoIntegradoItem.pedido_integrado_id == pedido.id,
        )
        .all()
    )
    return pedido, itens


def _restaurar_pendencia_legada_por_incidente(
    db: Session,
    *,
    tenant_id,
    pedido: PedidoIntegrado,
) -> None:
    payload = pedido.payload if isinstance(pedido.payload, dict) else {}
    retorno_atual = (
        payload.get("retorno_estoque")
        if isinstance(payload.get("retorno_estoque"), dict)
        else {}
    )
    if retorno_atual.get("status") in {
        "pendente",
        "retornado",
        "nao_retornado",
    }:
        return

    incidente = (
        db.query(BlingFlowIncident)
        .filter(
            BlingFlowIncident.tenant_id == tenant_id,
            BlingFlowIncident.code == INCIDENTE_RETORNO_ESTOQUE_PENDENTE,
            BlingFlowIncident.status.in_(["open", "ignored"]),
            BlingFlowIncident.pedido_integrado_id == pedido.id,
        )
        .order_by(BlingFlowIncident.id.desc())
        .first()
    )
    if not incidente:
        return

    detalhes = incidente.details if isinstance(incidente.details, dict) else {}
    pedido.payload = {
        **payload,
        "retorno_estoque": {
            **detalhes,
            "nf_id": detalhes.get("nf_id")
            or getattr(incidente, "nf_bling_id", None),
            "status": "pendente",
            "origem": "incidente",
        },
    }
    db.add(pedido)
    db.flush()


@router.post("/pedidos/{pedido_id}/solicitar-cancelamento-nf")
def solicitar_cancelamento_nf_pedido(
    pedido_id: int,
    request: SolicitarCancelamentoNFRequest,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    pedido, _itens = _buscar_pedido_com_itens(
        db,
        tenant_id=tenant_id,
        pedido_id=pedido_id,
    )
    if pedido.status != "cancelado":
        raise HTTPException(
            status_code=400,
            detail="Somente pedidos cancelados podem cancelar a NF vinculada",
        )

    try:
        resultado = solicitar_cancelamento_nf_bling(
            db,
            pedido=pedido,
            justificativa=request.justificativa,
            automatico=False,
            forcar=True,
        )
        if not resultado.get("success"):
            raise ValueError(
                "Este pedido nao possui uma NF ativa vinculada para cancelar"
            )
        db.commit()
        return resultado
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception(
            "[BLING PEDIDOS] Falha ao solicitar cancelamento da NF do pedido %s: %s",
            pedido_id,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao solicitar cancelamento da NF no Bling: {exc}",
        ) from exc


@router.post("/pedidos/{pedido_id}/decidir-retorno-estoque")
def decidir_retorno_estoque_pedido(
    pedido_id: int,
    request: DecisaoRetornoEstoqueRequest,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_tenant
    pedido, itens = _buscar_pedido_com_itens(
        db,
        tenant_id=tenant_id,
        pedido_id=pedido_id,
    )

    try:
        _restaurar_pendencia_legada_por_incidente(
            db,
            tenant_id=tenant_id,
            pedido=pedido,
        )
        return decidir_retorno_estoque(
            db,
            pedido=pedido,
            itens=itens,
            acao=request.acao,
            motivo=request.motivo,
            user_id=getattr(user, "id", None),
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception(
            "[BLING PEDIDOS] Falha na decisao de estoque do pedido %s: %s",
            pedido_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao aplicar decisao de estoque: {exc}",
        ) from exc
