"""Captura o custo original comprovável dos itens devolvidos."""

import json
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.empresa_grupo_estoque_compartilhado_service import (
    contexto_tenant_estoque,
    resolver_tenant_estoque_item,
)
from app.produtos_models import EstoqueMovimentacao
from app.services.venda_rentabilidade_snapshot_service import SNAPSHOT_VERSION


CENTAVO = Decimal("0.01")


def _decimal(valor) -> Decimal:
    return Decimal(str(valor or 0))


def _moeda(valor) -> Decimal:
    return _decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _assinatura_item(item) -> tuple:
    return (
        getattr(item, "produto_id", None),
        _decimal(getattr(item, "quantidade", 0)),
        _moeda(getattr(item, "preco_unitario", 0)),
    )


def _assinatura_fotografia(fotografia) -> tuple:
    return (
        fotografia.get("produto_id"),
        _decimal(fotografia.get("quantidade")),
        _moeda(fotografia.get("preco_unitario")),
    )


def _custo_parcela(
    custo_original: Decimal,
    quantidade_original: Decimal,
    quantidade_anterior: Decimal,
    quantidade: Decimal,
) -> Decimal | None:
    """Diferenca de cotas cumulativas para preservar o custo ate o ultimo centavo."""
    if (
        quantidade_original <= 0
        or quantidade_anterior < 0
        or quantidade <= 0
        or quantidade_anterior + quantidade > quantidade_original
    ):
        return None
    antes = _moeda(custo_original * quantidade_anterior / quantidade_original)
    depois = _moeda(
        custo_original * (quantidade_anterior + quantidade) / quantidade_original
    )
    return depois - antes


def _custo_snapshot(
    venda, item, quantidade: Decimal, quantidade_anterior: Decimal = Decimal("0")
) -> Decimal | None:
    snapshot = getattr(venda, "rentabilidade_snapshot", None)
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except (TypeError, ValueError):
            return None
    if not isinstance(snapshot, dict):
        return None
    try:
        versao = int(snapshot.get("snapshot_version") or 0)
    except (TypeError, ValueError):
        return None
    if versao < SNAPSHOT_VERSION:
        return None

    itens_venda = list(getattr(venda, "itens", []) or [])
    itens_snapshot = snapshot.get("itens")
    if not isinstance(itens_snapshot, list) or len(itens_venda) != len(itens_snapshot):
        return None
    assinatura = _assinatura_item(item)
    quantidade_original = assinatura[1]
    if (
        quantidade_original <= 0
        or quantidade_anterior < 0
        or quantidade <= 0
        or quantidade_anterior + quantidade > quantidade_original
    ):
        return None
    if sum(_assinatura_item(outro) == assinatura for outro in itens_venda) != 1:
        return None
    if not all(isinstance(fotografia, dict) for fotografia in itens_snapshot):
        return None
    correspondencias = [
        fotografia
        for fotografia in itens_snapshot
        if _assinatura_fotografia(fotografia) == assinatura
    ]
    if len(correspondencias) != 1:
        return None
    custo_original = _moeda(correspondencias[0].get("custo_total"))
    return (
        _custo_parcela(
            custo_original, quantidade_original, quantidade_anterior, quantidade
        )
        if custo_original > 0
        else None
    )


def custo_original_item_devolvido(
    db: Session,
    venda,
    item,
    quantidade: Decimal,
    tenant_id,
    quantidade_anterior: Decimal = Decimal("0"),
) -> tuple[Decimal, str, bool]:
    """Nunca usa o preço de custo atual como se fosse o custo na data da venda."""
    custo_snapshot = _custo_snapshot(venda, item, quantidade, quantidade_anterior)
    if custo_snapshot is not None:
        return custo_snapshot, "snapshot_venda", False

    produto_id = getattr(item, "produto_id", None)
    if str(getattr(item, "tipo", "") or "").lower() != "produto" or not produto_id:
        return Decimal("0"), "sem_custo_original", True

    # A saída de estoque é vinculada ao produto e à venda, não à linha vendida.
    # Com mais de uma linha do mesmo produto, o custo individual é ambíguo.
    if (
        sum(
            getattr(outro, "produto_id", None) == produto_id
            for outro in (getattr(venda, "itens", []) or [])
        )
        != 1
    ):
        return Decimal("0"), "sem_custo_original", True

    tenant_estoque, _ = resolver_tenant_estoque_item(item, tenant_id)
    with contexto_tenant_estoque(tenant_estoque, tenant_id) as tenant_estoque_uuid:
        quantidade_saida, valor_saida = (
            db.query(
                func.coalesce(func.sum(EstoqueMovimentacao.quantidade), 0),
                func.coalesce(func.sum(EstoqueMovimentacao.valor_total), 0),
            )
            .filter(
                EstoqueMovimentacao.tenant_id == tenant_estoque_uuid,
                EstoqueMovimentacao.referencia_tipo == "venda",
                EstoqueMovimentacao.referencia_id == venda.id,
                EstoqueMovimentacao.produto_id == produto_id,
                EstoqueMovimentacao.tipo == "saida",
                EstoqueMovimentacao.status != "cancelado",
            )
            .one()
        )
    quantidade_saida = abs(_decimal(quantidade_saida))
    valor_saida = abs(_decimal(valor_saida))
    # Movimentos extras do mesmo produto (inclusive componentes de kit) não
    # podem ser atribuídos com segurança à linha devolvida.
    if quantidade_saida == _decimal(getattr(item, "quantidade", 0)) and valor_saida > 0:
        custo_parcela = _custo_parcela(
            valor_saida, quantidade_saida, quantidade_anterior, quantidade
        )
        if custo_parcela is not None:
            return custo_parcela, "saida_estoque_venda", False
    return Decimal("0"), "sem_custo_original", True
