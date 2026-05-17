from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.produtos_models import Produto, ProdutoLote


def _calcular_status_validade(dias_para_vencer: Optional[int]) -> str:
    """Classifica o lote conforme a proximidade do vencimento."""
    if dias_para_vencer is None:
        return "sem_validade"
    if dias_para_vencer < 0:
        return "vencido"
    if dias_para_vencer <= 7:
        return "urgente"
    if dias_para_vencer <= 30:
        return "alerta_30"
    if dias_para_vencer <= 60:
        return "alerta_60"
    return "monitorar"


def _calcular_faixa_campanha_validade(dias_para_vencer: Optional[int]) -> Optional[str]:
    """Sugere uma faixa comercial para campanhas por vencimento."""
    if dias_para_vencer is None:
        return None
    if dias_para_vencer < 0:
        return "vencido"
    if dias_para_vencer <= 7:
        return "7_dias"
    if dias_para_vencer <= 30:
        return "30_dias"
    if dias_para_vencer <= 60:
        return "60_dias"
    return None


def _mapa_validade_proxima_produtos(
    db: Session,
    produtos: list[Produto],
    tenant_ids: list[Any],
) -> dict[int, dict[str, Any]]:
    produto_ids = [produto.id for produto in produtos if getattr(produto, "id", None)]
    if not produto_ids:
        return {}

    rows = (
        db.query(
            ProdutoLote.id,
            ProdutoLote.produto_id,
            ProdutoLote.nome_lote,
            ProdutoLote.data_validade,
            ProdutoLote.quantidade_inicial,
            ProdutoLote.quantidade_disponivel,
        )
        .filter(
            ProdutoLote.produto_id.in_(produto_ids),
            ProdutoLote.tenant_id.in_(tenant_ids),
            ProdutoLote.status != "excluido",
            func.coalesce(ProdutoLote.quantidade_disponivel, 0) > 0,
        )
        .order_by(
            ProdutoLote.produto_id.asc(),
            ProdutoLote.data_validade.is_(None).asc(),
            ProdutoLote.data_validade.asc(),
            ProdutoLote.ordem_entrada.asc(),
            ProdutoLote.id.asc(),
        )
        .all()
    )

    validade_por_produto: dict[int, dict[str, Any]] = {}
    for (
        lote_id,
        produto_id,
        nome_lote,
        data_validade,
        quantidade_inicial,
        quantidade_disponivel,
    ) in rows:
        validade_info = validade_por_produto.setdefault(
            produto_id,
            {
                "validade_proxima_listagem": None,
                "lote_validade_proxima": None,
                "lotes_validade_resumo": [],
            },
        )

        if data_validade and not validade_info["validade_proxima_listagem"]:
            validade_info["validade_proxima_listagem"] = data_validade
            validade_info["lote_validade_proxima"] = nome_lote

        validade_info["lotes_validade_resumo"].append(
            {
                "id": lote_id,
                "nome_lote": nome_lote,
                "data_validade": data_validade,
                "quantidade_inicial": float(quantidade_inicial or 0),
                "quantidade_disponivel": float(quantidade_disponivel or 0),
            }
        )

    return validade_por_produto

