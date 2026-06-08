"""Rotas de rateio de notas de entrada."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.fiscal import (
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
)
from app.notas_entrada.schemas import RateioItemRequest, RateioNotaRequest
from app.produtos_models import NotaEntrada, NotaEntradaItem

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{nota_id}/rateio")
def configurar_rateio_nota(
    nota_id: int,
    rateio: RateioNotaRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Configura tipo de rateio da nota inteira:
    - 'online': 100% online
    - 'loja': 100% loja fisica
    - 'parcial': configurar por produto
    """
    _, tenant_id = user_and_tenant

    if rateio.tipo_rateio not in ["online", "loja", "parcial"]:
        raise HTTPException(status_code=400, detail="Tipo de rateio invalido. Use: online, loja ou parcial")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(
            NotaEntrada.id == nota_id,
            NotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    nota.tipo_rateio = rateio.tipo_rateio

    if rateio.tipo_rateio == "online":
        nota.percentual_online = 100
        nota.percentual_loja = 0
        nota.valor_online = nota.valor_total
        nota.valor_loja = 0

        for item in nota.itens:
            item.quantidade_online = 0
            item.valor_online = 0

    elif rateio.tipo_rateio == "loja":
        nota.percentual_online = 0
        nota.percentual_loja = 100
        nota.valor_online = 0
        nota.valor_loja = nota.valor_total

        for item in nota.itens:
            item.quantidade_online = 0
            item.valor_online = 0

    else:
        nota.percentual_online = 0
        nota.percentual_loja = 100
        nota.valor_online = 0
        nota.valor_loja = nota.valor_total

    db.commit()
    db.refresh(nota)

    logger.info("Rateio da nota configurado: %s", rateio.tipo_rateio)

    return {
        "message": "Tipo de rateio configurado com sucesso",
        "nota_id": nota.id,
        "tipo_rateio": nota.tipo_rateio,
        "percentual_online": nota.percentual_online,
        "percentual_loja": nota.percentual_loja,
        "valor_online": nota.valor_online,
        "valor_loja": nota.valor_loja,
    }


@router.post("/{nota_id}/itens/{item_id}/rateio")
def configurar_rateio_item(
    nota_id: int,
    item_id: int,
    rateio: RateioItemRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Configura quantidade do item que e online (para rateio parcial).
    Sistema calcula automaticamente os percentuais da nota.
    """
    _, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(
            NotaEntrada.id == nota_id,
            NotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    if nota.tipo_rateio != "parcial":
        raise HTTPException(
            status_code=400,
            detail="Nota nao esta configurada como rateio parcial. Configure primeiro o tipo de rateio.",
        )

    item = (
        db.query(NotaEntradaItem)
        .filter(
            NotaEntradaItem.id == item_id,
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.tenant_id == tenant_id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item nao encontrado")

    dados_pack = calcular_quantidade_custo_efetivos(
        item.descricao,
        item.quantidade,
        item.valor_unitario,
        item.valor_total,
    )
    quantidade_total_disponivel = dados_pack["quantidade_efetiva"]
    composicao_custo = calcular_composicao_custos_nota(nota).get(item.id, {})
    custo_unitario_efetivo = composicao_custo.get(
        "custo_aquisicao_unitario",
        dados_pack["custo_unitario_efetivo"],
    )

    if rateio.quantidade_online < 0:
        raise HTTPException(status_code=400, detail="Quantidade online nao pode ser negativa")

    if rateio.quantidade_online > quantidade_total_disponivel:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Quantidade online ({rateio.quantidade_online}) nao pode ser maior "
                f"que a quantidade total ({quantidade_total_disponivel})"
            ),
        )

    item.quantidade_online = rateio.quantidade_online
    item.valor_online = rateio.quantidade_online * custo_unitario_efetivo

    valor_online_total = 0
    for it in nota.itens:
        if it.id == item_id:
            valor_online_total += item.valor_online
        else:
            valor_online_total += it.valor_online or 0

    nota.valor_online = valor_online_total
    nota.valor_loja = nota.valor_total - valor_online_total
    nota.percentual_online = (valor_online_total / nota.valor_total * 100) if nota.valor_total > 0 else 0
    nota.percentual_loja = 100 - nota.percentual_online

    db.commit()
    db.refresh(item)
    db.refresh(nota)

    logger.info(
        "Rateio item configurado - %s: %s/%s online = R$ %.2f",
        item.descricao,
        item.quantidade_online,
        item.quantidade,
        item.valor_online,
    )
    logger.info(
        "Nota %s: %.1f%% online (R$ %.2f) | %.1f%% loja (R$ %.2f)",
        nota.numero_nota,
        nota.percentual_online,
        nota.valor_online,
        nota.percentual_loja,
        nota.valor_loja,
    )

    return {
        "message": "Rateio do item configurado com sucesso",
        "item": {
            "id": item.id,
            "quantidade_total": quantidade_total_disponivel,
            "quantidade_online": item.quantidade_online,
            "valor_online": item.valor_online,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
        },
        "nota_totais": {
            "valor_total": nota.valor_total,
            "valor_online": nota.valor_online,
            "valor_loja": nota.valor_loja,
            "percentual_online": round(nota.percentual_online, 2),
            "percentual_loja": round(nota.percentual_loja, 2),
        },
    }
