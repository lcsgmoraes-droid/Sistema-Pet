from __future__ import annotations

from typing import Any, Optional


def calcular_totais_venda(
    itens: list[Any],
    desconto_valor: float,
    desconto_percentual: float,
    taxa_entrega: float,
) -> dict:
    """Calcula subtotal, desconto e total preservando desconto rateado por item."""
    subtotal_liquido = sum(float(item.subtotal or 0) for item in itens)
    desconto_itens = sum(float(item.desconto_item or 0) for item in itens)
    taxa_entrega = float(taxa_entrega or 0)

    if desconto_itens > 0:
        desconto_calculado = desconto_itens
        total = subtotal_liquido + taxa_entrega
    else:
        desconto_calculado = float(desconto_valor or 0)
        if desconto_percentual and desconto_percentual > 0:
            desconto_calculado = subtotal_liquido * (float(desconto_percentual) / 100)
        total = subtotal_liquido - desconto_calculado + taxa_entrega

    return {
        "subtotal": subtotal_liquido,
        "desconto_valor": round(desconto_calculado, 2),
        "total": total,
    }


def _resolver_status_entrega_atualizacao(
    tem_entrega: bool, status_atual: Optional[str]
) -> Optional[str]:
    if not tem_entrega:
        return None
    return status_atual or "pendente"
