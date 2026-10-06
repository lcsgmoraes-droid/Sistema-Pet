"""Custos de devolucao vinculados ao comprovante imutavel da baixa original."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.empresa_grupo_estoque_compartilhado_service import resolver_tenant_estoque_item


CENTAVO = Decimal("0.01")


def _decimal(valor) -> Decimal | None:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _moeda(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _custo_parcela(
    custo_original: Decimal,
    quantidade_original: Decimal,
    quantidade_anterior: Decimal,
    quantidade: Decimal,
) -> Decimal | None:
    """Diferenca de cotas cumulativas para preservar o ultimo centavo."""
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


def _custo_comprovante(
    venda, item, quantidade: Decimal, quantidade_anterior: Decimal, tenant_id
) -> Decimal | None:
    comprovante = getattr(item, "custo_original_saida", None)
    if not isinstance(comprovante, dict):
        return None

    quantidade_original = _decimal(getattr(item, "quantidade", None))
    quantidade_prova = _decimal(comprovante.get("quantidade"))
    custo_original = _decimal(comprovante.get("custo_total"))
    if quantidade_original is None or quantidade_prova != quantidade_original:
        return None
    if custo_original is None or custo_original <= 0:
        return None
    try:
        ids_validos = (
            int(comprovante.get("venda_id")) == int(venda.id)
            and int(comprovante.get("venda_item_id")) == int(item.id)
            and int(comprovante.get("produto_id")) == int(item.produto_id)
            and int(comprovante.get("movimentacao_id")) > 0
            and int(comprovante.get("versao")) == 1
        )
    except (TypeError, ValueError):
        return None
    if not ids_validos or comprovante.get("origem") != "baixa_estoque_venda":
        return None

    tenant_estoque, _ = resolver_tenant_estoque_item(item, tenant_id)
    if str(comprovante.get("tenant_estoque_id")) != str(tenant_estoque):
        return None

    return _custo_parcela(
        _moeda(custo_original), quantidade_original, quantidade_anterior, quantidade
    )


def custo_original_item_devolvido(
    db: Session,
    venda,
    item,
    quantidade: Decimal,
    tenant_id,
    quantidade_anterior: Decimal = Decimal("0"),
) -> tuple[Decimal, str, bool]:
    """Usa apenas custo capturado na baixa, nunca snapshot reprocessavel."""
    if str(getattr(item, "tipo", "") or "").lower() != "produto":
        # Servico prestado permanece custo incorrido, sem reversao na DRE.
        return Decimal("0"), "servico_custo_mantido", False

    custo = _custo_comprovante(venda, item, quantidade, quantidade_anterior, tenant_id)
    if custo is not None:
        return custo, "baixa_estoque_venda", False
    return Decimal("0"), "sem_custo_original", True
