from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto
from app.services.bling_flow_monitor_diagnostics_parts.context import _ultima_nf
from app.services.bling_flow_monitor_utils import _primeiro_preenchido, _text


def _produto_por_sku(
    db: Session, tenant_id, sku: str
) -> tuple[Produto | None, str | None]:
    if not sku:
        return None, None

    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(Produto.codigo == sku, Produto.codigo_barras == sku),
        )
        .first()
    )
    if not produto:
        return None, None
    if produto.codigo == sku:
        return produto, "codigo"
    if produto.codigo_barras == sku:
        return produto, "codigo_barras"
    return produto, "desconhecido"


def _contar_movimentacoes_saida_nf(
    db: Session,
    pedido: PedidoIntegrado,
    *,
    payload: dict | None,
) -> tuple[int, int]:
    from app.services.bling_nf_service import movimento_documentado_por_nf

    nf = _ultima_nf(payload)
    nf_id = _text(_primeiro_preenchido(nf.get("id"), nf.get("nfe_id")))
    nf_numero = _text(nf.get("numero"))
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .all()
    )
    total = len(movimentacoes)
    total_nf = sum(
        1
        for mov in movimentacoes
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_id)
    )
    return total, total_nf
