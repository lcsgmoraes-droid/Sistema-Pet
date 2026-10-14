from __future__ import annotations

from typing import Any, Optional

from app.services.venda_descontos import ZERO, _campo, liquido_item, moeda


def resolver_descontos_atualizacao(venda: Any, dados: Any) -> dict:
    """Clientes antigos podem omitir G/C ao editar uma venda do contrato novo."""
    informados = dados.model_fields_set
    global_atual = getattr(venda, "desconto_venda_valor", None)
    global_valor = (
        dados.desconto_venda_valor
        if "desconto_venda_valor" in informados
        else global_atual
    )
    codigo = dados.cupom_code
    cupom = dados.cupom_discount_applied
    if global_atual is not None and global_valor is not None:
        if "cupom_code" not in informados:
            codigo = venda.cupom_code
        if "cupom_discount_applied" not in informados:
            cupom = venda.cupom_discount_applied if codigo else 0
    return {
        "desconto_venda_valor": global_valor,
        "cupom_code": codigo,
        "cupom_discount_applied": cupom,
    }


def calcular_totais_venda(
    itens: list[Any],
    desconto_valor: float,
    desconto_percentual: float,
    taxa_entrega: float,
    *,
    desconto_venda_valor: Optional[float] = None,
    cupom_discount_applied: Optional[float] = None,
) -> dict:
    """G explicito usa o contrato Di/G/C; NULL conserva clientes legados."""
    if desconto_venda_valor is not None:
        subtotal = sum((liquido_item(item) for item in itens), ZERO)
        individuais = sum(
            (moeda(_campo(item, "desconto_item", 0)) for item in itens), ZERO
        )
        global_valor = moeda(desconto_venda_valor)
        cupom = moeda(cupom_discount_applied)
        frete = moeda(taxa_entrega)
        if (
            global_valor < 0
            or cupom < 0
            or frete < 0
            or global_valor + cupom > subtotal
        ):
            raise ValueError(
                "O desconto geral e o cupom nao podem exceder o valor dos itens."
            )
        return {
            "subtotal": float(moeda(subtotal)),
            "desconto_valor": float(moeda(individuais + global_valor + cupom)),
            "total": float(moeda(subtotal - global_valor - cupom + frete)),
        }

    subtotal_liquido = sum(float(_campo(item, "subtotal", 0) or 0) for item in itens)
    desconto_itens = sum(float(_campo(item, "desconto_item", 0) or 0) for item in itens)
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
