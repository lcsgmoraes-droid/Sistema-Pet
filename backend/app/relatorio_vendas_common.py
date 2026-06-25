"""Helpers compartilhados do relatorio de vendas."""

import json
from typing import Optional

from .produtos_models import Produto
from .promocoes_venda_utils import detectar_promocao_por_preco_vendido
from .vendas_models import Venda, VendaItem


STATUS_VENDA_RECEBIDA_INTEGRAL = {"finalizada", "pago_nf", "baixada", "paga"}
STATUS_VENDA_SEM_SALDO_ABERTO = STATUS_VENDA_RECEBIDA_INTEGRAL | {"cancelada"}


def _texto_normalizado(valor) -> str:
    return str(valor or "").strip().lower()


CANAIS_RELATORIO_ALIASES = {
    "pdv": "loja_fisica",
    "erp": "loja_fisica",
    "loja": "loja_fisica",
    "caixa": "loja_fisica",
    "balcao": "loja_fisica",
    "loja_fisica": "loja_fisica",
    "loja-fisica": "loja_fisica",
    "app": "app",
    "mobile": "app",
    "aplicativo": "app",
    "app_movel": "app",
    "ecommerce": "ecommerce",
    "e_commerce": "ecommerce",
    "e-commerce": "ecommerce",
    "loja_virtual": "ecommerce",
    "site": "ecommerce",
    "web": "ecommerce",
}


def _normalizar_canal_venda_relatorio(valor: Optional[str]) -> Optional[str]:
    texto = str(valor or "").strip().lower()
    if not texto:
        return None

    chave = texto.replace(" ", "_")
    return CANAIS_RELATORIO_ALIASES.get(chave, chave)


def _venda_tem_documento_fiscal(venda: Venda) -> bool:
    nfe_status = _texto_normalizado(getattr(venda, "nfe_status", None))
    if nfe_status in {"cancelada", "cancelado", "denegada", "rejeitada"}:
        return False

    return bool(
        getattr(venda, "nfe_bling_id", None)
        or getattr(venda, "nfe_chave", None)
        or getattr(venda, "nfe_numero", None)
        or _texto_normalizado(getattr(venda, "status", None)) == "pago_nf"
    )


def _normalizar_forma_pagamento_label(valor) -> str:
    texto = str(valor or "").strip()
    chave = texto.lower()
    mapa = {
        "1": "Dinheiro",
        "2": "Pix",
        "3": "Cartao Debito",
        "4": "Cartao Credito",
        "5": "Cartao Credito",
        "dinheiro": "Dinheiro",
        "pix": "Pix",
        "debito": "Cartao Debito",
        "cartao_debito": "Cartao Debito",
        "cartao debito": "Cartao Debito",
        "credito": "Cartao Credito",
        "cartao_credito": "Cartao Credito",
        "cartao credito": "Cartao Credito",
        "credito_parcelado": "Cartao Credito",
        "credito cliente": "Credito do Cliente",
        "credito_cliente": "Credito do Cliente",
    }
    return mapa.get(chave, texto or "Nao informado")


def _as_float(valor) -> float:
    try:
        if valor is None:
            return 0.0
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _total_recebido_venda(venda: Venda) -> float:
    pagamentos = list(getattr(venda, "pagamentos", []) or [])
    total_pagamentos = sum(
        _as_float(getattr(pagamento, "valor", 0)) for pagamento in pagamentos
    )
    if total_pagamentos > 0:
        total_venda = _as_float(getattr(venda, "total", 0))
        if total_venda > 0:
            return round(min(total_pagamentos, total_venda), 2)
        return round(total_pagamentos, 2)

    valor_recebido = _as_float(getattr(venda, "valor_recebido", 0))
    if valor_recebido > 0:
        total_venda = _as_float(getattr(venda, "total", 0))
        if total_venda > 0:
            return round(min(valor_recebido, total_venda), 2)
        return round(valor_recebido, 2)

    if (
        _texto_normalizado(getattr(venda, "status", None))
        in STATUS_VENDA_RECEBIDA_INTEGRAL
    ):
        return round(_as_float(getattr(venda, "total", 0)), 2)

    return 0.0


def _saldo_aberto_venda(venda: Venda) -> float:
    status = _texto_normalizado(getattr(venda, "status", None))
    if status in STATUS_VENDA_SEM_SALDO_ABERTO:
        return 0.0

    return round(
        max(_as_float(getattr(venda, "total", 0)) - _total_recebido_venda(venda), 0), 2
    )


def _valores_operacionais_venda(venda: Venda) -> dict[str, float]:
    """Valores comerciais da venda, antes de despesas de rentabilidade.

    Historicamente o campo Venda.subtotal pode representar duas coisas:
    - subtotal bruto, quando o desconto foi aplicado no fechamento;
    - subtotal ja liquido, quando o PDV rateou desconto nos itens.

    O relatorio operacional precisa separar: bruto real, desconto, liquido cobrado
    do cliente, recebido e saldo aberto.
    """
    subtotal = _as_float(getattr(venda, "subtotal", 0))
    desconto = _as_float(getattr(venda, "desconto_valor", 0))
    taxa_entrega = _as_float(getattr(venda, "taxa_entrega", 0))
    total = _as_float(getattr(venda, "total", 0))
    tolerancia = 0.03

    total_se_subtotal_liquido = subtotal + taxa_entrega
    total_se_subtotal_bruto = subtotal - desconto + taxa_entrega

    if desconto > 0 and abs(total - total_se_subtotal_liquido) <= tolerancia:
        valor_bruto = subtotal + desconto
    elif desconto > 0 and abs(total - total_se_subtotal_bruto) <= tolerancia:
        valor_bruto = subtotal
    else:
        valor_bruto_itens = sum(
            _as_float(getattr(item, "quantidade", 0))
            * _as_float(getattr(item, "preco_unitario", 0))
            for item in list(getattr(venda, "itens", []) or [])
        )
        if valor_bruto_itens > 0:
            valor_bruto = valor_bruto_itens
        elif desconto > 0:
            valor_bruto = max(subtotal, total - taxa_entrega + desconto)
        else:
            valor_bruto = subtotal

    valor_liquido = total
    valor_recebido = _total_recebido_venda(venda)

    return {
        "valor_bruto": round(valor_bruto, 2),
        "taxa_entrega": round(taxa_entrega, 2),
        "desconto": round(desconto, 2),
        "valor_liquido": round(valor_liquido, 2),
        "valor_recebido": round(valor_recebido, 2),
        "saldo_aberto": _saldo_aberto_venda(venda),
    }


def _valor_cupom_venda(venda: Venda, cupons_por_venda: dict[int, float]) -> float:
    valor_salvo = _as_float(getattr(venda, "cupom_discount_applied", 0))
    if valor_salvo > 0:
        return round(valor_salvo, 2)
    return round(_as_float(cupons_por_venda.get(venda.id, 0.0)), 2)


def _snapshot_dict(venda: Venda) -> dict:
    snapshot = getattr(venda, "rentabilidade_snapshot", None)
    if isinstance(snapshot, dict):
        return snapshot
    if isinstance(snapshot, str) and snapshot.strip():
        try:
            parsed = json.loads(snapshot)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _precisa_reclassificar_campanha(
    venda: Venda, custo_campanha: float, cupom_desconto: float
) -> bool:
    if custo_campanha <= 0 and cupom_desconto <= 0:
        return False

    snapshot = _snapshot_dict(venda)
    if not snapshot:
        return False

    campanha_snapshot = _as_float(snapshot.get("custo_campanha", 0))
    cupom_snapshot = _as_float(snapshot.get("cupom_desconto", 0))
    return campanha_snapshot <= 0 or cupom_snapshot < cupom_desconto


def _detectar_promocao_item(
    produto: Optional[Produto],
    item: Optional[VendaItem],
    venda: Optional[Venda],
    item_snapshot: Optional[dict] = None,
) -> dict:
    item_snapshot = item_snapshot or {}
    preco_unitario = float(
        getattr(item, "preco_unitario", None)
        or item_snapshot.get("preco_unitario", 0)
        or 0
    )
    quantidade = float(
        getattr(item, "quantidade", None) or item_snapshot.get("quantidade", 0) or 0
    )
    subtotal_item = float(
        getattr(item, "subtotal", None) or item_snapshot.get("venda_bruta", 0) or 0
    )
    return detectar_promocao_por_preco_vendido(
        produto,
        venda,
        preco_unitario=preco_unitario,
        quantidade=quantidade,
        subtotal_item=subtotal_item,
    )


def _enriquecer_itens_promocionais(
    venda: Venda, itens_snapshot: list[dict]
) -> list[dict]:
    itens_venda = list(getattr(venda, "itens", []) or [])
    usados = set()
    resultado = []

    for indice, item_snapshot in enumerate(itens_snapshot):
        item_modelo = None
        produto_id_snapshot = item_snapshot.get("produto_id")

        if indice < len(itens_venda):
            candidato = itens_venda[indice]
            if (
                not produto_id_snapshot
                or getattr(candidato, "produto_id", None) == produto_id_snapshot
            ):
                item_modelo = candidato
                usados.add(indice)

        if item_modelo is None:
            for idx, candidato in enumerate(itens_venda):
                if idx in usados:
                    continue
                if getattr(candidato, "produto_id", None) == produto_id_snapshot:
                    item_modelo = candidato
                    usados.add(idx)
                    break

        produto = getattr(item_modelo, "produto", None) if item_modelo else None
        info_promocao = _detectar_promocao_item(
            produto, item_modelo, venda, item_snapshot
        )
        resultado.append({**item_snapshot, **info_promocao})

    return resultado
