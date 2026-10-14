"""Comprovante de custo capturado na baixa da venda, antes de reprocessamentos."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.utils.timezone import now_brasilia


def _decimal(valor) -> Decimal | None:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def registrar_custo_original_saida(item, resultados, tenant_estoque) -> bool:
    """Registra uma unica saida inequivoca para a linha da venda, sem sobrescrever."""
    if getattr(item, "custo_original_saida", None) is not None:
        return False
    if str(getattr(item, "tipo", "") or "").lower() != "produto":
        return False

    quantidade_item = _decimal(getattr(item, "quantidade", None))
    if quantidade_item is None or quantidade_item <= 0:
        return False

    candidatos = [
        resultado
        for resultado in resultados or []
        if resultado.get("produto_id") == getattr(item, "produto_id", None)
        and resultado.get("movimentacao_id")
    ]
    if len(candidatos) != 1:
        return False
    resultado = candidatos[0]
    quantidade_saida = _decimal(resultado.get("quantidade"))
    custo_total = _decimal(resultado.get("valor_total"))
    if (
        quantidade_saida != quantidade_item
        or custo_total is None
        or custo_total <= 0
        or getattr(item, "id", None) is None
        or getattr(item, "venda_id", None) is None
        or not tenant_estoque
    ):
        return False

    item.custo_original_saida = {
        "versao": 1,
        "origem": "baixa_estoque_venda",
        "venda_id": int(item.venda_id),
        "venda_item_id": int(item.id),
        "produto_id": int(item.produto_id),
        "tenant_estoque_id": str(tenant_estoque),
        "movimentacao_id": int(resultado["movimentacao_id"]),
        "quantidade": str(quantidade_saida),
        "custo_total": str(
            custo_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        "capturado_em": now_brasilia().isoformat(),
    }
    return True
