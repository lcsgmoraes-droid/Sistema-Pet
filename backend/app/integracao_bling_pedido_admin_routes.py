from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque_reserva_service import EstoqueReservaService
from app.integracao_bling_nf_routes import _dict
from app.integracao_bling_pedido_payload import (
    _montar_payload_pedido,
    _serializar_pedido_bling,
)
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.services.pedido_integrado_duplicate_review_service import (
    consolidar_duplicidades_seguras_pedido,
    mapear_duplicidade_por_pedido_ids,
    reconciliar_fluxo_pedido_integrado,
)
from app.utils.logger import logger

router = APIRouter()


@router.get("/pedidos")
def listar_pedidos_bling(
    status: Optional[str] = Query(
        None, description="aberto|confirmado|expirado|cancelado"
    ),
    busca: Optional[str] = Query(
        None, description="Numero interno do pedido Bling ou ID do pedido"
    ),
    pedido: Optional[str] = Query(
        None, alias="pedido", description="Alias legado para o filtro de busca"
    ),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    q = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.tenant_id == tenant_id,
        PedidoIntegrado.status != "mesclado",
    )

    if status:
        q = q.filter(PedidoIntegrado.status == status)

    busca_texto = str(busca or pedido or "").strip()
    if busca_texto:
        termo = f"%{busca_texto}%"
        q = q.filter(
            or_(
                PedidoIntegrado.pedido_bling_numero.ilike(termo),
                PedidoIntegrado.pedido_bling_id.ilike(termo),
            )
        )

    total = q.count()
    pedidos = (
        q.order_by(PedidoIntegrado.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )
    duplicidade_por_pedido = mapear_duplicidade_por_pedido_ids(
        db,
        tenant_id=tenant_id,
        pedido_ids=[int(p.id) for p in pedidos if getattr(p, "id", None)],
    )

    result = []
    for p in pedidos:
        itens = (
            db.query(PedidoIntegradoItem)
            .filter(PedidoIntegradoItem.pedido_integrado_id == p.id)
            .all()
        )
        try:
            result.append(
                _serializar_pedido_bling(
                    p,
                    itens,
                    duplicidade=duplicidade_por_pedido.get(int(p.id)),
                )
            )
        except Exception as exc:
            logger.exception(
                "[BLING PEDIDOS] Falha ao serializar pedido local id=%s bling_id=%s numero=%s: %s",
                getattr(p, "id", None),
                getattr(p, "pedido_bling_id", None),
                getattr(p, "pedido_bling_numero", None),
                exc,
            )

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "pedidos": result,
    }


@router.post("/pedidos/reconciliar-status")
def reconciliar_status_pedidos_recentes(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(60, ge=1, le=500),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    from app.services.pedido_status_reconciliation_service import (
        reconciliar_status_pedidos_recentes as _reconciliar_status_pedidos_recentes,
    )

    try:
        return _reconciliar_status_pedidos_recentes(
            db,
            tenant_id,
            dias=dias,
            limite_pedidos=limite,
        )
    except Exception as exc:
        logger.exception(
            "[BLING PEDIDOS] Falha ao reconciliar status dos pedidos recentes: %s", exc
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao reconciliar status dos pedidos: {exc}"
        )


@router.post("/pedidos/reconciliar-duplicidades")
def reconciliar_duplicidades_pedidos_recentes(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    from app.services.pedido_duplicate_reconciliation_service import (
        reconciliar_duplicidades_recentes_pedido_loja as _reconciliar_duplicidades_recentes_pedido_loja,
    )

    try:
        return _reconciliar_duplicidades_recentes_pedido_loja(
            db,
            tenant_id,
            dias=dias,
            limite_grupos=limite,
        )
    except Exception as exc:
        logger.exception(
            "[BLING PEDIDOS] Falha ao reconciliar duplicidades recentes dos pedidos: %s",
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao reconciliar duplicidades dos pedidos: {exc}",
        )


@router.post("/pedidos/{pedido_id}/consolidar-duplicidade")
def consolidar_duplicidade_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    try:
        resultado = consolidar_duplicidades_seguras_pedido(
            db,
            tenant_id=tenant_id,
            pedido_id=pedido_id,
        )
    except Exception as exc:
        logger.exception(
            "[BLING PEDIDOS] Falha ao consolidar duplicidade do pedido %s: %s",
            pedido_id,
            exc,
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao consolidar duplicidade: {exc}"
        )

    if resultado.get("success"):
        return resultado

    motivo = resultado.get("motivo")
    if motivo == "pedido_nao_encontrado":
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if motivo == "pedido_sem_duplicidade":
        raise HTTPException(
            status_code=400, detail="Este pedido nao possui duplicidade ativa"
        )
    if motivo in {
        "pedido_sem_duplicidade_canonica",
        "duplicidades_requerem_revisao_manual",
        "nenhuma_duplicidade_segura_aplicada",
    }:
        raise HTTPException(status_code=409, detail=resultado)

    raise HTTPException(status_code=400, detail=resultado)


@router.post("/pedidos/{pedido_id}/reconciliar-fluxo")
def reconciliar_fluxo_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    try:
        resultado = reconciliar_fluxo_pedido_integrado(
            db,
            tenant_id=tenant_id,
            pedido_id=pedido_id,
        )
    except Exception as exc:
        logger.exception(
            "[BLING PEDIDOS] Falha ao reconciliar fluxo do pedido %s: %s",
            pedido_id,
            exc,
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao reconciliar fluxo do pedido: {exc}"
        )

    if resultado.get("success"):
        return resultado

    motivo = resultado.get("motivo")
    if motivo == "pedido_nao_encontrado":
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if motivo in {"pedido_sem_itens", "reconciliacao_sem_sucesso"}:
        raise HTTPException(status_code=409, detail=resultado)

    raise HTTPException(status_code=400, detail=resultado)


@router.post("/pedidos/{pedido_id}/confirmar-manual")
def confirmar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    from app.integracao_bling_pedido_routes import _confirmar_pedido

    tenant_id = user_tenant[1]
    user = user_tenant[0]

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

    if pedido.status not in ("aberto", "expirado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' nao pode ser confirmado manualmente",
        )

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )

    erros_estoque = _confirmar_pedido(
        db=db,
        pedido=pedido,
        itens=itens,
        motivo="venda_bling_manual",
        observacao="Confirmacao manual do pedido; venda aguardando NF",
        user_id=getattr(user, "id", 0),
        aplicar_baixa_estoque=False,
    )

    return {
        "status": "ok",
        "pedido_id": pedido.id,
        "erros_estoque": erros_estoque,
        "estoque_movimentado": False,
    }


@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido_manual(
    pedido_id: str,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    from app.integracao_bling_pedido_routes import _cancelar_pedido

    tenant_id = user_tenant[1]

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

    if pedido.status in ("confirmado", "cancelado"):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido com status '{pedido.status}' nao pode ser cancelado",
        )

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )

    _cancelar_pedido(db=db, pedido=pedido, itens=itens)

    return {"status": "ok", "pedido_id": pedido.id}


@router.post("/pedidos/reprocessar-sem-itens")
def reprocessar_pedidos_sem_itens(
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]

    subq_com_itens = (
        db.query(PedidoIntegradoItem.pedido_integrado_id).distinct().subquery()
    )
    pedidos_sem_itens = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.status.in_(["aberto", "expirado"]),
            PedidoIntegrado.id.notin_(subq_com_itens),
        )
        .limit(limite)
        .all()
    )

    if not pedidos_sem_itens:
        return {"reprocessados": 0, "message": "Nenhum pedido sem itens encontrado"}

    from app.bling_integration import BlingAPI

    _bling_api = BlingAPI()

    reprocessados = 0
    erros = []

    for pedido in pedidos_sem_itens:
        try:
            pedido_completo = _bling_api.consultar_pedido(pedido.pedido_bling_id)
            pedido.payload = _montar_payload_pedido(
                webhook_data=_dict((pedido.payload or {})).get("webhook"),
                pedido_completo=pedido_completo,
                payload_atual=pedido.payload,
            )
            db.add(pedido)
            itens_bling = pedido_completo.get("itens", [])
            if not itens_bling:
                db.commit()
                continue

            for item in itens_bling:
                sku = item.get("codigo") or item.get("sku")
                descricao = item.get("descricao")
                quantidade = int(float(item.get("quantidade", 0)))
                if not sku or quantidade <= 0:
                    continue
                item_pedido = PedidoIntegradoItem(
                    tenant_id=pedido.tenant_id,
                    pedido_integrado_id=pedido.id,
                    sku=sku,
                    descricao=descricao,
                    quantidade=quantidade,
                )
                try:
                    EstoqueReservaService.reservar(db, item_pedido)
                except ValueError:
                    pass
                db.add(item_pedido)

            db.commit()
            reprocessados += 1
        except Exception as e:
            erros.append(
                {"pedido_bling_id": pedido.pedido_bling_id, "erro": str(e)[:120]}
            )

    return {
        "reprocessados": reprocessados,
        "total_sem_itens": len(pedidos_sem_itens),
        "erros": erros,
    }
