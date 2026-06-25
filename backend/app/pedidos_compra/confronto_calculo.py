"""Calculo do confronto entre pedido de compra e notas de entrada."""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.produtos_models import PedidoCompra, Produto

logger = logging.getLogger(__name__)


def _float_confronto(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _calcular_composicoes_custo_confronto(notas: List) -> Dict[int, Dict[str, Any]]:
    """Reaproveita o custo final calculado na entrada da NF para o confronto."""
    try:
        from app import notas_entrada_routes
    except ImportError:
        logger.exception(
            "Nao foi possivel importar composicao de custos da NF para confronto"
        )
        return {}

    composicoes: Dict[int, Dict[str, Any]] = {}
    for nota in notas:
        try:
            composicoes.update(
                notas_entrada_routes.calcular_composicao_custos_nota(nota) or {}
            )
        except Exception:
            logger.exception(
                "Falha ao calcular custo final da NF no confronto pedido x nota",
                extra={"nota_entrada_id": getattr(nota, "id", None)},
            )
    return composicoes


def _valor_custo_final_item_nf(
    item_nf: Any, composicoes_custo: Dict[int, Dict[str, Any]]
) -> float:
    composicao = composicoes_custo.get(getattr(item_nf, "id", None)) or {}
    if composicao.get("custo_aquisicao_total") is not None:
        return _float_confronto(composicao.get("custo_aquisicao_total"))
    return _float_confronto(getattr(item_nf, "valor_total", 0))


def _preco_custo_final_item_nf(
    item_nf: Any, composicoes_custo: Dict[int, Dict[str, Any]]
) -> float:
    valor_total = _valor_custo_final_item_nf(item_nf, composicoes_custo)
    quantidade = _float_confronto(getattr(item_nf, "quantidade", 0))
    if quantidade:
        return valor_total / quantidade

    composicao = composicoes_custo.get(getattr(item_nf, "id", None)) or {}
    if composicao.get("custo_aquisicao_unitario") is not None:
        return _float_confronto(composicao.get("custo_aquisicao_unitario"))
    return _float_confronto(getattr(item_nf, "valor_unitario", 0))


def _status_item_confronto(
    dif_qtd: float, dif_preco_pct: float
) -> tuple[str, bool, bool]:
    divergiu_qtd = abs(dif_qtd) > 0.001
    divergiu_preco = abs(dif_preco_pct) > 0.5

    if divergiu_qtd and divergiu_preco:
        status_item = "divergencia_mista"
    elif divergiu_qtd:
        status_item = "divergencia_quantidade"
    elif divergiu_preco:
        status_item = "divergencia_preco"
    else:
        status_item = "ok"

    return status_item, divergiu_qtd, divergiu_preco


def _montar_item_confronto_encontrado(
    item_pedido,
    nome_produto,
    codigo_produto,
    item_nf_id,
    qtd_pedida,
    qtd_nf,
    preco_pedido,
    preco_nf,
    valor_pedido,
    valor_nf,
    extras: dict | None = None,
) -> tuple[dict, bool, bool]:
    dif_qtd = qtd_nf - qtd_pedida
    dif_preco_unit = preco_nf - preco_pedido
    dif_preco_pct = (
        ((preco_nf - preco_pedido) / preco_pedido * 100) if preco_pedido else 0
    )
    dif_valor = valor_nf - valor_pedido
    status_item, divergiu_qtd, divergiu_preco = _status_item_confronto(
        dif_qtd, dif_preco_pct
    )

    item = {
        "produto_id": item_pedido.produto_id,
        "produto_nome": nome_produto,
        "produto_codigo": codigo_produto,
        "item_pedido_id": item_pedido.id,
        "item_nf_id": item_nf_id,
        "qtd_pedida": qtd_pedida,
        "qtd_nf": qtd_nf,
        "dif_qtd": round(dif_qtd, 3),
        "preco_pedido": round(preco_pedido, 4),
        "preco_nf": round(preco_nf, 4),
        "dif_preco_unit": round(dif_preco_unit, 4),
        "dif_preco_pct": round(dif_preco_pct, 2),
        "valor_pedido": round(valor_pedido, 2),
        "valor_nf": round(valor_nf, 2),
        "dif_valor": round(dif_valor, 2),
        "status": status_item,
        "encontrado_na_nf": True,
    }
    if extras:
        item.update(extras)
    return item, divergiu_qtd, divergiu_preco


def _montar_item_confronto_nao_encontrado(
    item_pedido,
    nome_produto,
    codigo_produto,
    qtd_pedida,
    preco_pedido,
    valor_pedido,
    extras: dict | None = None,
) -> dict:
    item = {
        "produto_id": item_pedido.produto_id,
        "produto_nome": nome_produto,
        "produto_codigo": codigo_produto,
        "item_pedido_id": item_pedido.id,
        "item_nf_id": None,
        "qtd_pedida": qtd_pedida,
        "qtd_nf": 0,
        "dif_qtd": -qtd_pedida,
        "preco_pedido": round(preco_pedido, 4),
        "preco_nf": 0,
        "dif_preco_unit": None,
        "dif_preco_pct": 0,
        "valor_pedido": round(valor_pedido, 2),
        "valor_nf": 0,
        "dif_valor": -round(valor_pedido, 2),
        "status": "nao_encontrado",
        "encontrado_na_nf": False,
    }
    if extras:
        item.update(extras)
    return item


def _normalizar_notas_confronto(nota_ou_notas) -> List:
    if not nota_ou_notas:
        return []
    if isinstance(nota_ou_notas, (list, tuple, set)):
        return [n for n in nota_ou_notas if n]
    return [nota_ou_notas]


def _resumir_notas_confronto(notas: List) -> List[dict]:
    return [
        {
            "id": n.id,
            "numero_nota": n.numero_nota,
            "serie": n.serie,
            "chave_acesso": n.chave_acesso,
            "fornecedor_nome": n.fornecedor_nome,
            "data_emissao": n.data_emissao,
            "valor_total": n.valor_total,
        }
        for n in notas
    ]


def _formatar_numeros_notas(notas: List) -> str:
    numeros = [str(n.numero_nota) for n in notas if getattr(n, "numero_nota", None)]
    return ", ".join(numeros) if numeros else "-"


def _codigo_igual(valor_a, valor_b) -> bool:
    if valor_a is None or valor_b is None:
        return False
    return str(valor_a).strip() == str(valor_b).strip()


def _itens_nf_para_pedido_por_produto(itens_nf, itens_nf_usados, item_pedido) -> list:
    return [
        it
        for it in itens_nf
        if it.id not in itens_nf_usados and it.produto_id == item_pedido.produto_id
    ]


def _itens_nf_para_pedido_por_codigo(itens_nf, itens_nf_usados, campo, valor) -> list:
    if not valor:
        return []
    return [
        it
        for it in itens_nf
        if it.id not in itens_nf_usados
        and getattr(it, campo, None)
        and _codigo_igual(getattr(it, campo), valor)
    ]


def _itens_nf_para_pedido(
    itens_nf, itens_nf_usados, item_pedido, codigo_produto, ean_produto
) -> list:
    candidatos = _itens_nf_para_pedido_por_produto(
        itens_nf, itens_nf_usados, item_pedido
    )
    if candidatos:
        return candidatos

    candidatos = _itens_nf_para_pedido_por_codigo(
        itens_nf, itens_nf_usados, "ean", ean_produto
    )
    if candidatos:
        return candidatos

    return _itens_nf_para_pedido_por_codigo(
        itens_nf, itens_nf_usados, "codigo_produto", codigo_produto
    )


def _dados_produto_pedido(
    db: Session, item_pedido, tenant_id: int
) -> tuple[str, str, str]:
    produto = (
        db.query(Produto)
        .filter(Produto.id == item_pedido.produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        return f"Produto {item_pedido.produto_id}", None, None
    return produto.nome, produto.codigo, produto.codigo_barras


def _valores_item_pedido(item_pedido) -> tuple[float, float, float]:
    qtd_pedida = item_pedido.quantidade_pedida
    preco_pedido = item_pedido.preco_unitario - item_pedido.desconto_item
    valor_pedido = qtd_pedida * preco_pedido
    return qtd_pedida, preco_pedido, valor_pedido


def _extras_itens_nf(itens_match) -> dict:
    return {
        "item_nf_ids": [it.id for it in itens_match],
        "nota_entrada_ids": sorted(
            {it.nota_entrada_id for it in itens_match if it.nota_entrada_id}
        ),
    }


def _confrontar_item_pedido_encontrado(
    item_pedido,
    nome_produto,
    codigo_produto,
    qtd_pedida,
    preco_pedido,
    valor_pedido,
    itens_match,
    composicoes_custo,
) -> tuple[dict, float, bool, bool]:
    qtd_nf = sum(float(it.quantidade or 0) for it in itens_match)
    valor_nf = sum(
        _valor_custo_final_item_nf(it, composicoes_custo) for it in itens_match
    )
    preco_nf = (
        (valor_nf / qtd_nf)
        if qtd_nf
        else _preco_custo_final_item_nf(itens_match[0], composicoes_custo)
    )
    item, divergiu_qtd, divergiu_preco = _montar_item_confronto_encontrado(
        item_pedido,
        nome_produto,
        codigo_produto,
        itens_match[0].id,
        qtd_pedida,
        qtd_nf,
        preco_pedido,
        preco_nf,
        valor_pedido,
        valor_nf,
        extras=_extras_itens_nf(itens_match),
    )
    return item, valor_nf, divergiu_qtd, divergiu_preco


def _confrontar_item_pedido(
    db: Session,
    item_pedido,
    itens_nf,
    itens_nf_usados,
    composicoes_custo,
    tenant_id: int,
) -> tuple[dict, float, float, bool, bool]:
    nome_produto, codigo_produto, ean_produto = _dados_produto_pedido(
        db, item_pedido, tenant_id
    )
    qtd_pedida, preco_pedido, valor_pedido = _valores_item_pedido(item_pedido)
    itens_match = _itens_nf_para_pedido(
        itens_nf, itens_nf_usados, item_pedido, codigo_produto, ean_produto
    )
    if not itens_match:
        item = _montar_item_confronto_nao_encontrado(
            item_pedido,
            nome_produto,
            codigo_produto,
            qtd_pedida,
            preco_pedido,
            valor_pedido,
            extras={"item_nf_ids": [], "nota_entrada_ids": []},
        )
        return item, valor_pedido, 0.0, True, False

    for item_nf in itens_match:
        itens_nf_usados.add(item_nf.id)
    item, valor_nf, divergiu_qtd, divergiu_preco = _confrontar_item_pedido_encontrado(
        item_pedido,
        nome_produto,
        codigo_produto,
        qtd_pedida,
        preco_pedido,
        valor_pedido,
        itens_match,
        composicoes_custo,
    )
    return item, valor_pedido, valor_nf, divergiu_qtd, divergiu_preco


def _montar_item_nf_nao_pedido(item_nf, composicoes_custo) -> tuple[dict, float]:
    qtd_nf = _float_confronto(item_nf.quantidade)
    valor_nf = _valor_custo_final_item_nf(item_nf, composicoes_custo)
    preco_nf = _preco_custo_final_item_nf(item_nf, composicoes_custo)
    return (
        {
            "produto_id": item_nf.produto_id,
            "produto_nome": item_nf.descricao,
            "produto_codigo": item_nf.codigo_produto,
            "item_pedido_id": None,
            "item_nf_id": item_nf.id,
            "item_nf_ids": [item_nf.id],
            "nota_entrada_ids": [item_nf.nota_entrada_id]
            if item_nf.nota_entrada_id
            else [],
            "qtd_pedida": 0,
            "qtd_nf": qtd_nf,
            "dif_qtd": qtd_nf,
            "preco_pedido": 0,
            "preco_nf": round(preco_nf, 4),
            "dif_preco_unit": None,
            "dif_preco_pct": 0,
            "valor_pedido": 0,
            "valor_nf": round(valor_nf, 2),
            "dif_valor": round(valor_nf, 2),
            "status": "nao_pedido",
            "encontrado_na_nf": True,
        },
        valor_nf,
    )


def _status_confronto(tem_divergencia_qtd: bool, tem_divergencia_preco: bool) -> str:
    if tem_divergencia_qtd and tem_divergencia_preco:
        return "divergencia_mista"
    if tem_divergencia_qtd:
        return "divergencia_quantidade"
    if tem_divergencia_preco:
        return "divergencia_preco"
    return "sem_divergencia"


def _resumo_confronto(
    pedido: PedidoCompra,
    notas: List,
    itens_nf: List,
    total_pedido: float,
    total_nf: float,
) -> dict:
    return {
        "total_pedido": round(total_pedido, 2),
        "total_nf": round(total_nf, 2),
        "dif_total": round(total_nf - total_pedido, 2),
        "frete_pedido": pedido.valor_frete,
        "frete_nf": round(sum(float(n.valor_frete or 0) for n in notas), 2),
        "desconto_pedido": pedido.valor_desconto,
        "desconto_nf": round(sum(float(n.valor_desconto or 0) for n in notas), 2),
        "itens_pedido": len(pedido.itens),
        "itens_nf": len(itens_nf),
        "notas_count": len(notas),
        "nota_entrada_ids": [n.id for n in notas],
        "numeros_nota": _formatar_numeros_notas(notas),
        "notas_entrada": _resumir_notas_confronto(notas),
    }


def _realizar_confronto(
    pedido: PedidoCompra, nota_ou_notas, db: Session, tenant_id: int
) -> dict:
    """Gera o confronto completo entre pedido e uma ou mais NF-e."""
    notas = _normalizar_notas_confronto(nota_ou_notas)
    itens_nf = [item for nota in notas for item in (nota.itens or [])]
    composicoes_custo = _calcular_composicoes_custo_confronto(notas)

    itens_confronto = []
    total_pedido = 0.0
    total_nf = 0.0
    tem_divergencia_qtd = False
    tem_divergencia_preco = False
    itens_nf_usados = set()

    for item_pedido in pedido.itens:
        item, valor_pedido, valor_nf, divergiu_qtd, divergiu_preco = (
            _confrontar_item_pedido(
                db,
                item_pedido,
                itens_nf,
                itens_nf_usados,
                composicoes_custo,
                tenant_id,
            )
        )
        itens_confronto.append(item)
        total_pedido += valor_pedido
        total_nf += valor_nf
        tem_divergencia_qtd = tem_divergencia_qtd or divergiu_qtd
        tem_divergencia_preco = tem_divergencia_preco or divergiu_preco

    for item_nf in itens_nf:
        if item_nf.id in itens_nf_usados:
            continue
        item, valor_nf = _montar_item_nf_nao_pedido(item_nf, composicoes_custo)
        itens_confronto.append(item)
        total_nf += valor_nf

    return {
        "status_confronto": _status_confronto(
            tem_divergencia_qtd, tem_divergencia_preco
        ),
        "itens": itens_confronto,
        "resumo": _resumo_confronto(pedido, notas, itens_nf, total_pedido, total_nf),
    }
