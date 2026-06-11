from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from typing import Any, Iterable, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload

from app.produtos_models import EstoqueMovimentacao
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)
from app.vendas_models import Venda, VendaItem


def _as_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _round_money(value: Any) -> float:
    return round(_as_float(value), 2)


def _as_start_datetime(value: Optional[date | datetime | str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    parsed = datetime.fromisoformat(str(value))
    return parsed.replace(hour=0, minute=0, second=0, microsecond=0)


def _as_end_datetime(value: Optional[date | datetime | str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(hour=23, minute=59, second=59, microsecond=999999)
    if isinstance(value, date):
        return datetime.combine(value, time.max)
    parsed = datetime.fromisoformat(str(value))
    return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)


def _normalizar_ids(venda_ids: Optional[Iterable[int]]) -> list[int]:
    ids = []
    vistos = set()
    for raw_id in venda_ids or []:
        try:
            venda_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if venda_id > 0 and venda_id not in vistos:
            ids.append(venda_id)
            vistos.add(venda_id)
    return ids


def _buscar_vendas(
    db: Session,
    tenant_id: Any,
    *,
    venda_ids: Optional[Iterable[int]] = None,
    data_inicio: Optional[date | datetime | str] = None,
    data_fim: Optional[date | datetime | str] = None,
    canal_venda: Optional[str] = None,
) -> list[Venda]:
    filtros = [
        Venda.tenant_id == tenant_id,
        or_(Venda.status.is_(None), Venda.status != "cancelada"),
    ]

    ids = _normalizar_ids(venda_ids)
    if ids:
        filtros.append(Venda.id.in_(ids))
    else:
        inicio = _as_start_datetime(data_inicio)
        fim = _as_end_datetime(data_fim)
        if inicio is not None:
            filtros.append(Venda.data_venda >= inicio)
        if fim is not None:
            filtros.append(Venda.data_venda <= fim)
        if canal_venda:
            filtros.append(Venda.canal == canal_venda)

    return (
        db.query(Venda)
        .options(selectinload(Venda.itens).selectinload(VendaItem.produto))
        .filter(and_(*filtros))
        .order_by(Venda.data_venda.asc(), Venda.id.asc())
        .all()
    )


def _corrigir_movimentacoes_custo_atual(
    db: Session,
    tenant_id: Any,
    vendas: list[Venda],
) -> dict[int, dict[int, dict[str, float]]]:
    venda_ids = [venda.id for venda in vendas]
    if not venda_ids:
        return {}

    movimentos = (
        db.query(EstoqueMovimentacao)
        .options(selectinload(EstoqueMovimentacao.produto))
        .filter(
            and_(
                EstoqueMovimentacao.tenant_id == tenant_id,
                EstoqueMovimentacao.referencia_tipo == "venda",
                EstoqueMovimentacao.referencia_id.in_(venda_ids),
                EstoqueMovimentacao.tipo == "saida",
                EstoqueMovimentacao.status != "cancelado",
            )
        )
        .all()
    )

    custos_por_venda: dict[int, dict[int, dict[str, float]]] = defaultdict(dict)
    for movimento in movimentos:
        produto = getattr(movimento, "produto", None)
        custo_unitario = _round_money(getattr(produto, "preco_custo", 0))
        quantidade = abs(_as_float(getattr(movimento, "quantidade", 0)))
        valor_total = _round_money(quantidade * custo_unitario)

        movimento.custo_unitario = custo_unitario
        movimento.valor_total = valor_total

        produto_id = getattr(movimento, "produto_id", None)
        if not produto_id:
            continue
        atual = custos_por_venda[movimento.referencia_id].setdefault(
            produto_id,
            {"quantidade": 0.0, "valor_total": 0.0},
        )
        atual["quantidade"] += quantidade
        atual["valor_total"] += valor_total

    return custos_por_venda


def reprocessar_rentabilidade_vendas(
    db: Session,
    *,
    tenant_id: Any,
    venda_ids: Optional[Iterable[int]] = None,
    data_inicio: Optional[date | datetime | str] = None,
    data_fim: Optional[date | datetime | str] = None,
    canal_venda: Optional[str] = None,
) -> dict[str, Any]:
    vendas = _buscar_vendas(
        db,
        tenant_id,
        venda_ids=venda_ids,
        data_inicio=data_inicio,
        data_fim=data_fim,
        canal_venda=canal_venda,
    )
    custos_por_venda = _corrigir_movimentacoes_custo_atual(db, tenant_id, vendas)

    itens_resultado = []
    for venda in vendas:
        snapshot_anterior = getattr(venda, "rentabilidade_snapshot", None) or {}
        custo_anterior = (
            _round_money(snapshot_anterior.get("custo_produtos", 0))
            if isinstance(snapshot_anterior, dict)
            else 0.0
        )
        snapshot = get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=True,
            force_refresh=True,
            estoque_custos_por_produto=custos_por_venda.get(venda.id, {}),
        )
        itens_resultado.append(
            {
                "venda_id": venda.id,
                "numero_venda": venda.numero_venda,
                "custo_anterior": custo_anterior,
                "custo_novo": _round_money(snapshot.get("custo_produtos", 0)),
                "lucro_novo": _round_money(snapshot.get("lucro", 0)),
            }
        )

    return {
        "total_encontrado": len(vendas),
        "total_reprocessado": len(vendas),
        "vendas": itens_resultado,
    }
