import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.comissoes_models import ComissaoItem
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.financeiro_models import FormaPagamento
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao
from app.utils.timezone import now_brasilia

logger = logging.getLogger(__name__)

SNAPSHOT_VERSION = 1
FROZEN_STATUSES = {"finalizada", "baixa_parcial"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _round_money(value: Any) -> float:
    return round(_as_float(value), 2)


def _normalize_forma_pagamento(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _load_existing_snapshot(raw_snapshot: Any) -> Optional[Dict[str, Any]]:
    if isinstance(raw_snapshot, dict):
        return raw_snapshot

    if isinstance(raw_snapshot, str) and raw_snapshot.strip():
        try:
            parsed = json.loads(raw_snapshot)
        except Exception:
            logger.warning("Nao foi possivel desserializar rentabilidade_snapshot legado.")
            return None
        if isinstance(parsed, dict):
            return parsed

    return None


def _get_formas_pagamento_map(db: Session, tenant_id: Any) -> Dict[str, FormaPagamento]:
    formas = db.query(FormaPagamento).filter(
        and_(FormaPagamento.tenant_id == tenant_id, FormaPagamento.ativo == True)
    ).all()
    return {_normalize_forma_pagamento(fp.nome): fp for fp in formas}


def _resolve_taxa_cartao_total(
    venda: Any,
    formas_pagamento_map: Dict[str, FormaPagamento],
) -> float:
    taxa_total = 0.0

    for pagamento in list(getattr(venda, "pagamentos", []) or []):
        taxa_percentual = 0.0
        forma_pagamento = _normalize_forma_pagamento(getattr(pagamento, "forma_pagamento", None))
        forma = formas_pagamento_map.get(forma_pagamento)

        if forma:
            taxas_por_parcela = getattr(forma, "taxas_por_parcela", None)
            if isinstance(taxas_por_parcela, str):
                try:
                    taxas_por_parcela = json.loads(taxas_por_parcela)
                except Exception:
                    taxas_por_parcela = None

            numero_parcelas = getattr(pagamento, "numero_parcelas", None)
            if isinstance(taxas_por_parcela, dict) and numero_parcelas:
                taxa_percentual = _as_float(taxas_por_parcela.get(str(numero_parcelas), 0))
            else:
                taxa_percentual = _as_float(getattr(forma, "taxa_percentual", 0))

        taxa_total += _as_float(getattr(pagamento, "valor", 0)) * taxa_percentual / 100.0

    return _round_money(taxa_total)


def _resolve_impostos_percentual(
    db: Session,
    tenant_id: Any,
    impostos_percentual: Optional[float],
) -> float:
    if impostos_percentual is not None:
        return _as_float(impostos_percentual)

    try:
        config_fiscal = db.query(EmpresaConfigFiscal).filter(
            EmpresaConfigFiscal.tenant_id == tenant_id
        ).first()
        return _as_float(getattr(config_fiscal, "aliquota_simples_vigente", 0))
    except Exception as exc:
        logger.warning("Falha ao buscar configuracao fiscal para snapshot da venda: %s", exc)
        return 0.0


def _resolve_comissao_total(
    db: Session,
    tenant_id: Any,
    venda_id: int,
    comissao_total: Optional[float],
) -> float:
    if comissao_total is not None:
        return _round_money(comissao_total)

    try:
        total = db.query(func.sum(ComissaoItem.valor_comissao)).filter(
            and_(ComissaoItem.tenant_id == tenant_id, ComissaoItem.venda_id == venda_id)
        ).scalar()
        return _round_money(total)
    except Exception as exc:
        logger.warning("Falha ao buscar comissoes para snapshot da venda %s: %s", venda_id, exc)
        return 0.0


def _resolve_custo_campanha(
    db: Session,
    tenant_id: Any,
    venda_id: int,
    custo_campanha: Optional[float],
) -> float:
    if custo_campanha is not None:
        return _round_money(custo_campanha)

    try:
        from app.campaigns.models import CashbackTransaction

        total = db.query(func.sum(CashbackTransaction.amount)).filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.amount < 0,
            CashbackTransaction.source_id == venda_id,
        ).scalar()
        return _round_money(abs(total or 0))
    except Exception as exc:
        logger.warning("Falha ao buscar custo de campanha da venda %s: %s", venda_id, exc)
        return 0.0


def _resolve_taxa_operacional_entrega(
    db: Session,
    tenant_id: Any,
    venda: Any,
    taxa_operacional_entrega: Optional[float],
) -> float:
    if taxa_operacional_entrega is not None:
        return _round_money(taxa_operacional_entrega)

    if not getattr(venda, "tem_entrega", False) or not getattr(venda, "entregador_id", None):
        return 0.0

    try:
        entregador = db.query(Cliente).filter(
            and_(Cliente.id == venda.entregador_id, Cliente.tenant_id == tenant_id)
        ).first()
        return _round_money(getattr(entregador, "taxa_fixa_entrega", 0))
    except Exception as exc:
        logger.warning("Falha ao buscar taxa operacional de entrega da venda %s: %s", venda.id, exc)
        return 0.0


def _resolve_estoque_costs_map(
    db: Session,
    tenant_id: Any,
    venda_id: int,
    estoque_custos_por_produto: Optional[Dict[int, Dict[str, float]]],
) -> Dict[int, Dict[str, float]]:
    if estoque_custos_por_produto is not None:
        return estoque_custos_por_produto

    movimentos = db.query(EstoqueMovimentacao).filter(
        and_(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.referencia_tipo == "venda",
            EstoqueMovimentacao.referencia_id == venda_id,
            EstoqueMovimentacao.tipo == "saida",
        )
    ).all()

    mapa: Dict[int, Dict[str, float]] = {}
    for movimento in movimentos:
        if not movimento.produto_id:
            continue
        atual = mapa.setdefault(movimento.produto_id, {"quantidade": 0.0, "valor_total": 0.0})
        atual["quantidade"] += abs(_as_float(getattr(movimento, "quantidade", 0)))
        atual["valor_total"] += abs(_as_float(getattr(movimento, "valor_total", 0)))

    return mapa


def _resolve_custo_unitario_item(item: Any, estoque_custos_por_produto: Dict[int, Dict[str, float]]) -> float:
    produto_id = getattr(item, "produto_id", None)
    info_mov = estoque_custos_por_produto.get(produto_id or 0)
    if info_mov and _as_float(info_mov.get("quantidade", 0)) > 0:
        return _round_money(_as_float(info_mov.get("valor_total", 0)) / _as_float(info_mov.get("quantidade", 1)))

    produto = getattr(item, "produto", None)
    return _round_money(getattr(produto, "preco_custo", 0))


def build_venda_rentabilidade_snapshot(
    venda: Any,
    db: Session,
    tenant_id: Any,
    *,
    impostos_percentual: Optional[float] = None,
    formas_pagamento_map: Optional[Dict[str, FormaPagamento]] = None,
    custo_campanha: Optional[float] = None,
    comissao_total: Optional[float] = None,
    taxa_operacional_entrega: Optional[float] = None,
    estoque_custos_por_produto: Optional[Dict[int, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    formas_pagamento_map = formas_pagamento_map or _get_formas_pagamento_map(db, tenant_id)
    estoque_custos_por_produto = _resolve_estoque_costs_map(
        db, tenant_id, venda.id, estoque_custos_por_produto
    )

    taxa_cartao_total = _resolve_taxa_cartao_total(venda, formas_pagamento_map)
    comissao_total = _resolve_comissao_total(db, tenant_id, venda.id, comissao_total)
    impostos_percentual = _resolve_impostos_percentual(db, tenant_id, impostos_percentual)
    taxa_operacional_entrega = _resolve_taxa_operacional_entrega(
        db, tenant_id, venda, taxa_operacional_entrega
    )
    custo_campanha = _resolve_custo_campanha(db, tenant_id, venda.id, custo_campanha)

    taxa_entrega_receita = _round_money(getattr(venda, "taxa_entrega", 0))
    taxa_entrega_repasse = _round_money(getattr(venda, "valor_taxa_entregador", 0))
    if taxa_entrega_repasse < 0:
        taxa_entrega_repasse = 0.0
    if taxa_entrega_repasse > taxa_entrega_receita:
        taxa_entrega_repasse = taxa_entrega_receita

    venda_bruta = _round_money(_as_float(getattr(venda, "subtotal", 0)) + _as_float(getattr(venda, "desconto_valor", 0)))
    desconto_total = _round_money(getattr(venda, "desconto_valor", 0))

    itens_base = []
    subtotal_itens = 0.0
    custo_total = 0.0

    for item in list(getattr(venda, "itens", []) or []):
        quantidade = _as_float(getattr(item, "quantidade", 0))
        preco_unitario = _as_float(getattr(item, "preco_unitario", 0))
        subtotal_item = _round_money(quantidade * preco_unitario)
        custo_unitario = _resolve_custo_unitario_item(item, estoque_custos_por_produto)
        custo_item = _round_money(custo_unitario * quantidade)

        itens_base.append(
            {
                "item": item,
                "quantidade": quantidade,
                "preco_unitario": preco_unitario,
                "subtotal_item": subtotal_item,
                "custo_unitario": custo_unitario,
                "custo_item": custo_item,
            }
        )
        subtotal_itens += subtotal_item
        custo_total += custo_item

    itens_snapshot = []
    for item_base in itens_base:
        item = item_base["item"]
        subtotal_item = item_base["subtotal_item"]
        percentual_item = (subtotal_item / subtotal_itens) if subtotal_itens > 0 else 0.0

        desconto_rateado = desconto_total * percentual_item
        taxa_loja_rateada = taxa_entrega_receita * percentual_item
        taxa_entrega_rateada = taxa_entrega_repasse * percentual_item
        taxa_operacional_rateada = taxa_operacional_entrega * percentual_item
        taxa_cartao_rateada = taxa_cartao_total * percentual_item
        comissao_rateada = comissao_total * percentual_item
        campanha_rateada = custo_campanha * percentual_item
        imposto_rateado = (subtotal_item + taxa_loja_rateada) * (impostos_percentual / 100.0)

        valor_liquido_item = (
            subtotal_item
            + taxa_loja_rateada
            - desconto_rateado
            - taxa_entrega_rateada
            - taxa_operacional_rateada
            - taxa_cartao_rateada
            - comissao_rateada
            - imposto_rateado
            - campanha_rateada
        )
        lucro_item = valor_liquido_item - item_base["custo_item"]
        margem_sobre_venda_item = (lucro_item / subtotal_item * 100.0) if subtotal_item > 0 else 0.0
        margem_sobre_custo_item = (lucro_item / item_base["custo_item"] * 100.0) if item_base["custo_item"] > 0 else 0.0
        lucro_unitario = (lucro_item / item_base["quantidade"]) if item_base["quantidade"] > 0 else 0.0

        produto = getattr(item, "produto", None)
        itens_snapshot.append(
            {
                "produto_id": getattr(item, "produto_id", None),
                "produto_nome": getattr(produto, "nome", None) or "Produto removido",
                "quantidade": _round_money(item_base["quantidade"]),
                "preco_unitario": _round_money(item_base["preco_unitario"]),
                "venda_bruta": _round_money(subtotal_item),
                "taxa_loja": _round_money(taxa_loja_rateada),
                "desconto": _round_money(desconto_rateado),
                "taxa_entrega": _round_money(taxa_entrega_rateada),
                "taxa_operacional": _round_money(taxa_operacional_rateada),
                "taxa_cartao": _round_money(taxa_cartao_rateada),
                "comissao": _round_money(comissao_rateada),
                "imposto": _round_money(imposto_rateado),
                "campanha": _round_money(campanha_rateada),
                "valor_liquido": _round_money(valor_liquido_item),
                "custo_unitario": _round_money(item_base["custo_unitario"]),
                "custo_total": _round_money(item_base["custo_item"]),
                "lucro": _round_money(lucro_item),
                "lucro_unitario": _round_money(lucro_unitario),
                "margem_sobre_venda": round(margem_sobre_venda_item, 1),
                "margem_sobre_custo": round(margem_sobre_custo_item, 1),
            }
        )

    imposto_total = (venda_bruta + taxa_entrega_receita) * (impostos_percentual / 100.0)
    venda_liquida = (
        venda_bruta
        + taxa_entrega_receita
        - desconto_total
        - taxa_entrega_repasse
        - taxa_operacional_entrega
        - taxa_cartao_total
        - comissao_total
        - imposto_total
        - custo_campanha
    )
    lucro = venda_liquida - custo_total
    margem_sobre_venda = (lucro / venda_bruta * 100.0) if venda_bruta > 0 else 0.0
    margem_sobre_custo = (lucro / custo_total * 100.0) if custo_total > 0 else 0.0

    congelado = getattr(venda, "status", None) in FROZEN_STATUSES
    snapshot_em = now_brasilia().isoformat()

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "snapshot_em": snapshot_em,
        "snapshot_congelado": congelado,
        "venda_id": getattr(venda, "id", None),
        "numero_venda": getattr(venda, "numero_venda", None),
        "status": getattr(venda, "status", None),
        "data_venda": getattr(venda, "data_venda", None).isoformat() if getattr(venda, "data_venda", None) else None,
        "cliente_nome": getattr(getattr(venda, "cliente", None), "nome", None) or "Sem cliente",
        "venda_bruta": _round_money(venda_bruta),
        "taxa_loja": _round_money(taxa_entrega_receita),
        "desconto": _round_money(desconto_total),
        "taxa_entrega": _round_money(taxa_entrega_repasse),
        "taxa_operacional": _round_money(taxa_operacional_entrega),
        "taxa_cartao": _round_money(taxa_cartao_total),
        "comissao": _round_money(comissao_total),
        "imposto": _round_money(imposto_total),
        "impostos_percentual": round(impostos_percentual, 4),
        "custo_campanha": _round_money(custo_campanha),
        "venda_liquida": _round_money(venda_liquida),
        "custo_produtos": _round_money(custo_total),
        "lucro": _round_money(lucro),
        "margem_sobre_venda": round(margem_sobre_venda, 1),
        "margem_sobre_custo": round(margem_sobre_custo, 1),
        "itens": itens_snapshot,
    }


def get_or_build_venda_rentabilidade_snapshot(
    venda: Any,
    db: Session,
    tenant_id: Any,
    *,
    persist_if_missing: bool = True,
    force_refresh: bool = False,
    impostos_percentual: Optional[float] = None,
    formas_pagamento_map: Optional[Dict[str, FormaPagamento]] = None,
    custo_campanha: Optional[float] = None,
    comissao_total: Optional[float] = None,
    taxa_operacional_entrega: Optional[float] = None,
    estoque_custos_por_produto: Optional[Dict[int, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    status_atual = getattr(venda, "status", None)

    if not force_refresh and status_atual in FROZEN_STATUSES:
        existing = _load_existing_snapshot(getattr(venda, "rentabilidade_snapshot", None))
        if existing and int(existing.get("snapshot_version") or 0) == SNAPSHOT_VERSION:
            return existing

    snapshot = build_venda_rentabilidade_snapshot(
        venda,
        db,
        tenant_id,
        impostos_percentual=impostos_percentual,
        formas_pagamento_map=formas_pagamento_map,
        custo_campanha=custo_campanha,
        comissao_total=comissao_total,
        taxa_operacional_entrega=taxa_operacional_entrega,
        estoque_custos_por_produto=estoque_custos_por_produto,
    )

    if persist_if_missing and status_atual in FROZEN_STATUSES:
        venda.rentabilidade_snapshot = snapshot
        venda.rentabilidade_snapshot_em = now_brasilia()
        db.flush()

    return snapshot


def invalidate_venda_rentabilidade_snapshot(venda: Any) -> None:
    venda.rentabilidade_snapshot = None
    venda.rentabilidade_snapshot_em = None
