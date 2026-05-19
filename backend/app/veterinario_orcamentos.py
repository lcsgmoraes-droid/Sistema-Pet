"""Calculos e serializacao de orcamentos veterinarios."""

from typing import Iterable, Mapping, Optional

from .veterinario_financeiro import _as_float, _round_money
from .veterinario_models import OrcamentoVet, OrcamentoVetItem


ORIGENS_ORCAMENTO = {"catalogo", "produto", "diaria", "manual"}


def _quantidade(value) -> float:
    quantidade = _as_float(value)
    if quantidade is None or quantidade <= 0:
        return 1.0
    return quantidade


def _texto(value: Optional[str]) -> Optional[str]:
    texto = (value or "").strip()
    return texto or None


def _margem(preco_total: float, custo_total: float) -> tuple[float, float]:
    margem_valor = _round_money(preco_total - custo_total)
    margem_percentual = round((margem_valor / preco_total) * 100, 2) if preco_total > 0 else 0.0
    return margem_valor, margem_percentual


def _montar_item_base(
    *,
    origem: str,
    nome: str,
    quantidade,
    custo_unitario_estimado,
    preco_unitario_sugerido,
    preco_unitario=None,
    catalogo_id: Optional[int] = None,
    produto_id: Optional[int] = None,
    descricao: Optional[str] = None,
    unidade: Optional[str] = None,
    insumos: Optional[list[dict]] = None,
    observacoes: Optional[str] = None,
) -> dict:
    quantidade_normalizada = _quantidade(quantidade)
    custo_unitario = _round_money(custo_unitario_estimado)
    preco_sugerido = _round_money(preco_unitario_sugerido)
    preco_cobrado = _round_money(preco_unitario if preco_unitario is not None else preco_sugerido)
    custo_total = _round_money(custo_unitario * quantidade_normalizada)
    preco_total = _round_money(preco_cobrado * quantidade_normalizada)
    margem_valor, margem_percentual = _margem(preco_total, custo_total)

    return {
        "origem": origem if origem in ORIGENS_ORCAMENTO else "manual",
        "catalogo_id": catalogo_id,
        "produto_id": produto_id,
        "nome": (nome or "").strip() or "Item do orcamento",
        "descricao": _texto(descricao),
        "unidade": _texto(unidade),
        "quantidade": quantidade_normalizada,
        "custo_unitario_estimado": custo_unitario,
        "preco_unitario_sugerido": preco_sugerido,
        "preco_unitario": preco_cobrado,
        "custo_total_estimado": custo_total,
        "preco_total": preco_total,
        "margem_valor": margem_valor,
        "margem_percentual": margem_percentual,
        "insumos": insumos or [],
        "observacoes": _texto(observacoes),
        "baixar_estoque": False,
    }


def montar_item_orcamento_catalogo(
    catalogo,
    produtos_por_id: Mapping[int, object],
    *,
    quantidade=1,
    preco_unitario=None,
    observacoes: Optional[str] = None,
) -> dict:
    insumos = []
    custo_unitario_estimado = 0.0
    preco_insumos_sugerido = 0.0

    for insumo in getattr(catalogo, "insumos", None) or []:
        produto_id = insumo.get("produto_id") if isinstance(insumo, dict) else None
        produto = produtos_por_id.get(int(produto_id)) if produto_id else None
        if not produto:
            continue

        quantidade_insumo = _quantidade(insumo.get("quantidade"))
        custo_unitario = _round_money(getattr(produto, "preco_custo", 0))
        preco_unitario_produto = _round_money(getattr(produto, "preco_venda", 0))
        custo_total = _round_money(custo_unitario * quantidade_insumo)
        preco_total = _round_money(preco_unitario_produto * quantidade_insumo)
        custo_unitario_estimado = _round_money(custo_unitario_estimado + custo_total)
        preco_insumos_sugerido = _round_money(preco_insumos_sugerido + preco_total)

        insumos.append({
            "produto_id": int(produto_id),
            "nome": insumo.get("nome") or getattr(produto, "nome", None),
            "unidade": insumo.get("unidade") or getattr(produto, "unidade", None),
            "quantidade": quantidade_insumo,
            "custo_unitario": custo_unitario,
            "custo_total": custo_total,
            "preco_unitario_sugerido": preco_unitario_produto,
            "preco_total_sugerido": preco_total,
            "baixar_estoque": False,
        })

    valor_catalogo = _as_float(getattr(catalogo, "valor_padrao", None))
    preco_sugerido = valor_catalogo if valor_catalogo is not None else preco_insumos_sugerido

    return _montar_item_base(
        origem="catalogo",
        catalogo_id=getattr(catalogo, "id", None),
        nome=getattr(catalogo, "nome", None) or "Procedimento",
        descricao=getattr(catalogo, "descricao", None),
        quantidade=quantidade,
        custo_unitario_estimado=custo_unitario_estimado,
        preco_unitario_sugerido=preco_sugerido,
        preco_unitario=preco_unitario,
        insumos=insumos,
        observacoes=observacoes,
    )


def montar_item_orcamento_produto(
    produto,
    *,
    quantidade=1,
    preco_unitario=None,
    observacoes: Optional[str] = None,
) -> dict:
    return _montar_item_base(
        origem="produto",
        produto_id=getattr(produto, "id", None),
        nome=getattr(produto, "nome", None) or "Produto",
        unidade=getattr(produto, "unidade", None),
        quantidade=quantidade,
        custo_unitario_estimado=getattr(produto, "preco_custo", 0),
        preco_unitario_sugerido=getattr(produto, "preco_venda", 0),
        preco_unitario=preco_unitario,
        observacoes=observacoes,
    )


def montar_item_orcamento_manual(payload: dict) -> dict:
    origem = (payload.get("origem") or "manual").strip().lower()
    if origem not in ORIGENS_ORCAMENTO:
        origem = "manual"
    return _montar_item_base(
        origem=origem,
        nome=payload.get("nome") or ("Diaria de internacao" if origem == "diaria" else "Item do orcamento"),
        descricao=payload.get("descricao"),
        unidade=payload.get("unidade"),
        quantidade=payload.get("quantidade", 1),
        custo_unitario_estimado=payload.get("custo_unitario_estimado", 0),
        preco_unitario_sugerido=payload.get("preco_unitario_sugerido", payload.get("preco_unitario", 0)),
        preco_unitario=payload.get("preco_unitario"),
        insumos=payload.get("insumos") or [],
        observacoes=payload.get("observacoes"),
    )


def calcular_totais_orcamento(itens: Iterable[dict]) -> dict:
    custo_total = _round_money(sum((_as_float(item.get("custo_total_estimado")) or 0) for item in itens))
    preco_total = _round_money(sum((_as_float(item.get("preco_total")) or 0) for item in itens))
    margem_valor, margem_percentual = _margem(preco_total, custo_total)
    return {
        "custo_total_estimado": custo_total,
        "preco_total": preco_total,
        "margem_valor": margem_valor,
        "margem_percentual": margem_percentual,
    }


def serializar_item_orcamento(item: OrcamentoVetItem) -> dict:
    return {
        "id": item.id,
        "orcamento_id": item.orcamento_id,
        "origem": item.origem,
        "ordem": item.ordem,
        "catalogo_id": item.catalogo_id,
        "produto_id": item.produto_id,
        "nome": item.nome,
        "descricao": item.descricao,
        "unidade": item.unidade,
        "quantidade": _as_float(item.quantidade) or 0,
        "custo_unitario_estimado": _round_money(item.custo_unitario_estimado),
        "preco_unitario_sugerido": _round_money(item.preco_unitario_sugerido),
        "preco_unitario": _round_money(item.preco_unitario),
        "custo_total_estimado": _round_money(item.custo_total_estimado),
        "preco_total": _round_money(item.preco_total),
        "margem_valor": _round_money(item.margem_valor),
        "margem_percentual": round(_as_float(item.margem_percentual) or 0.0, 2),
        "insumos": item.insumos or [],
        "observacoes": item.observacoes,
        "baixar_estoque": False,
    }


def serializar_orcamento(orcamento: OrcamentoVet) -> dict:
    itens = sorted(orcamento.itens or [], key=lambda item: (item.ordem, item.id or 0))
    return {
        "id": orcamento.id,
        "consulta_id": orcamento.consulta_id,
        "internacao_id": orcamento.internacao_id,
        "pet_id": orcamento.pet_id,
        "cliente_id": orcamento.cliente_id,
        "veterinario_id": orcamento.veterinario_id,
        "titulo": orcamento.titulo,
        "status": orcamento.status,
        "previsao_dias_internacao": orcamento.previsao_dias_internacao,
        "observacoes": orcamento.observacoes,
        "custo_total_estimado": _round_money(orcamento.custo_total_estimado),
        "preco_total": _round_money(orcamento.preco_total),
        "margem_valor": _round_money(orcamento.margem_valor),
        "margem_percentual": round(_as_float(orcamento.margem_percentual) or 0.0, 2),
        "itens": [serializar_item_orcamento(item) for item in itens],
        "created_at": orcamento.created_at,
        "updated_at": orcamento.updated_at,
    }
