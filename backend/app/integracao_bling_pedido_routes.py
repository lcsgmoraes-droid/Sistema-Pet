
import os
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - Pedido"]
)


# ============================================================
# GET /integracoes/bling/pedidos  — listagem com filtros
# ============================================================

@router.get("/pedidos")
def listar_pedidos_bling(
    status: Optional[str] = Query(None, description="aberto|confirmado|expirado|cancelado"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    q = db.query(PedidoIntegrado).filter(PedidoIntegrado.tenant_id == tenant_id)

    if status:
        q = q.filter(PedidoIntegrado.status == status)

    total = q.count()
    pedidos = (
        q.order_by(PedidoIntegrado.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    result = []
    for p in pedidos:
        itens = db.query(PedidoIntegradoItem).filter(
            PedidoIntegradoItem.pedido_integrado_id == p.id
        ).all()

        result.append({
            "id": p.id,
            "pedido_bling_id": p.pedido_bling_id,
            "pedido_bling_numero": p.pedido_bling_numero,
            "canal": p.canal,
            "status": p.status,
            "criado_em": p.criado_em.isoformat() if p.criado_em else None,
            "expira_em": p.expira_em.isoformat() if p.expira_em else None,
            "confirmado_em": p.confirmado_em.isoformat() if p.confirmado_em else None,
            "cancelado_em": p.cancelado_em.isoformat() if p.cancelado_em else None,
            "itens": [
                {
                    "id": it.id,
                    "sku": it.sku,
                    "descricao": it.descricao,
                    "quantidade": it.quantidade,
                    "reservado_em": it.reservado_em.isoformat() if it.reservado_em else None,
                    "liberado_em": it.liberado_em.isoformat() if it.liberado_em else None,
                    "vendido_em": it.vendido_em.isoformat() if it.vendido_em else None,
                }
                for it in itens
            ],
        })

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "pedidos": result,
    }


# ============================================================
# POST /integracoes/bling/pedidos/{id}/confirmar-manual
# ============================================================

@router.post("/pedidos/{pedido_id}/confirmar-manual")
def confirmar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    user = user_tenant[0]

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido_id,
        PedidoIntegrado.tenant_id == tenant_id,
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ("aberto", "expirado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' não pode ser confirmado manualmente",
        )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    erros_estoque = []
    for item in itens:
        if item.vendido_em:
            continue  # já confirmado

        EstoqueReservaService.confirmar_venda(db, item)

        # Baixar estoque real
        try:
            from app.estoque.service import EstoqueService
            from app.produtos_models import Produto

            produto = db.query(Produto).filter(
                Produto.sku == item.sku,
                Produto.tenant_id == tenant_id,
            ).first()

            if produto:
                EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=float(item.quantidade),
                    motivo="venda_bling_manual",
                    referencia_id=pedido.id,
                    referencia_tipo="pedido_integrado",
                    user_id=getattr(user, "id", 0),
                    db=db,
                    tenant_id=tenant_id,
                    documento=pedido.pedido_bling_numero,
                    observacao=f"Baixa manual via tela Pedidos Bling",
                )
            else:
                erros_estoque.append(f"SKU '{item.sku}' não encontrado")
        except Exception as e:
            erros_estoque.append(f"SKU '{item.sku}': {str(e)[:80]}")
            logger.warning(f"[BLING MANUAL] Erro ao baixar estoque SKU {item.sku}: {e}")

    pedido.status = "confirmado"
    pedido.confirmado_em = datetime.utcnow()
    db.add(pedido)
    db.commit()

    return {
        "status": "ok",
        "pedido_id": pedido.id,
        "erros_estoque": erros_estoque,
    }


# ============================================================
# POST /integracoes/bling/pedidos/{id}/cancelar
# ============================================================

@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido_id,
        PedidoIntegrado.tenant_id == tenant_id,
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status in ("confirmado", "cancelado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' não pode ser cancelado",
        )

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    for item in itens:
        if not item.liberado_em and not item.vendido_em:
            EstoqueReservaService.liberar(db, item)

    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.utcnow()
    db.add(pedido)
    db.commit()

    return {"status": "ok", "pedido_id": pedido.id}


# Situações do pedido Bling que indicam cancelamento
_SITUACOES_PEDIDO_CANCELADO = {
    9,   # Cancelado
    10,  # Cancelado pelo comprador
    11,  # Cancelado por não pagamento
}


@router.post("/pedido")
async def receber_pedido_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de pedidos do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'order.created'|'order.updated'|'order.deleted', data: {...} }
    """
    body = await request.json()

    # Tenant fixo para webhooks (chamadas sem JWT)
    _tenant_uuid = UUID(_BLING_WEBHOOK_TENANT_ID) if _BLING_WEBHOOK_TENANT_ID else None
    if _tenant_uuid:
        set_current_tenant(_tenant_uuid)

    # Desempacotar envelope Bling (v1)
    event = body.get("event", "")  # ex: "order.created"
    data = body.get("data", body)  # fallback p/ payload legado sem envelope

    pedido_bling_id = str(data.get("id", ""))
    if not pedido_bling_id or pedido_bling_id == "None":
        return {"status": "ignorado", "motivo": "sem_id"}

    # ========================
    # EVENTO: EXCLUÍDO
    # ========================
    if event.endswith(".deleted"):
        pedido = db.query(PedidoIntegrado).filter(
            PedidoIntegrado.pedido_bling_id == pedido_bling_id
        ).first()
        if pedido and pedido.status not in ("confirmado", "cancelado"):
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            for item in itens:
                if not item.liberado_em and not item.vendido_em:
                    EstoqueReservaService.liberar(db, item)
            pedido.status = "cancelado"
            pedido.cancelado_em = datetime.utcnow()
            db.add(pedido)
            db.commit()
        return {"status": "ok", "acao": "cancelado"}

    # ========================
    # EVENTO: ATUALIZADO — checar se pedido foi cancelado no Bling
    # ========================
    if event.endswith(".updated"):
        situacao_id = data.get("situacao", {}).get("id") if isinstance(data.get("situacao"), dict) else None
        if situacao_id and int(situacao_id) in _SITUACOES_PEDIDO_CANCELADO:
            pedido = db.query(PedidoIntegrado).filter(
                PedidoIntegrado.pedido_bling_id == pedido_bling_id
            ).first()
            if pedido and pedido.status not in ("confirmado", "cancelado"):
                itens = db.query(PedidoIntegradoItem).filter(
                    PedidoIntegradoItem.pedido_integrado_id == pedido.id
                ).all()
                for item in itens:
                    if not item.liberado_em and not item.vendido_em:
                        EstoqueReservaService.liberar(db, item)
                pedido.status = "cancelado"
                pedido.cancelado_em = datetime.utcnow()
                db.add(pedido)
                db.commit()
            return {"status": "ok", "acao": "cancelado_por_situacao"}
        # updated sem cancelamento — ignorar para não duplicar reservas
        return {"status": "ignorado", "motivo": "order_updated_sem_cancelamento"}

    # ========================
    # EVENTO: CRIADO
    # ========================
    # Idempotência
    existente = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.pedido_bling_id == pedido_bling_id
    ).first()
    if existente:
        return {"status": "ignorado", "motivo": "pedido_ja_existe"}

    numero = data.get("numero")
    canal = str(data.get("loja", {}).get("id", "online")) if isinstance(data.get("loja"), dict) else "online"

    # O webhook NÃO inclui itens — buscar na API do Bling
    itens_bling = []
    try:
        from app.bling_integration import BlingAPI
        pedido_completo = BlingAPI().consultar_pedido(pedido_bling_id)
        itens_bling = pedido_completo.get("itens", [])
    except Exception as e:
        logger.warning(f"[BLING WEBHOOK] Falha ao buscar itens do pedido {pedido_bling_id}: {e}")

    if not _tenant_uuid:
        logger.error("[BLING WEBHOOK] BLING_WEBHOOK_TENANT_ID não configurado — pedido ignorado")
        return {"status": "erro", "motivo": "tenant_nao_configurado"}

    pedido = PedidoIntegrado(
        tenant_id=_tenant_uuid,
        pedido_bling_id=pedido_bling_id,
        pedido_bling_numero=numero,
        canal=canal,
        status="aberto",
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload=data
    )

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    for item in itens_bling:
        # Bling usa "codigo" como SKU no item de pedido
        sku = item.get("codigo") or item.get("sku")
        descricao = item.get("descricao")
        quantidade = int(float(item.get("quantidade", 0)))

        if not sku or quantidade <= 0:
            continue

        item_pedido = PedidoIntegradoItem(
            tenant_id=_tenant_uuid,
            pedido_integrado_id=pedido.id,
            sku=sku,
            descricao=descricao,
            quantidade=quantidade
        )

        EstoqueReservaService.reservar(db, item_pedido)
        db.add(item_pedido)

    db.commit()
    return {"status": "ok", "pedido_id": pedido.id}
