"""Helpers de relatorios de produtos e movimentacoes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.promocoes_venda_utils import detectar_promocao_por_preco_vendido
from app.produtos.core import _produto_sku_value
from app.produtos_models import EstoqueMovimentacao
from app.vendas_models import Venda, VendaItem


def _parse_relatorio_datetime(valor: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    texto = (valor or "").strip()
    if not texto:
        return None

    try:
        data = datetime.fromisoformat(texto)
    except ValueError:
        return None

    if end_of_day:
        return data.replace(hour=23, minute=59, second=59, microsecond=999999)
    return data.replace(hour=0, minute=0, second=0, microsecond=0)


def _detectar_promocao_venda_item(item: VendaItem) -> dict:
    venda = item.venda
    produto = item.produto
    preco_unitario = float(item.preco_unitario or 0)
    quantidade = float(item.quantidade or 0)
    subtotal = float(item.subtotal or 0)
    return detectar_promocao_por_preco_vendido(
        produto,
        venda,
        preco_unitario=preco_unitario,
        quantidade=quantidade,
        subtotal_item=subtotal,
    )


def _mapear_promocoes_movimentacoes(
    db: Session,
    tenant_id: int,
    movimentacoes: list[EstoqueMovimentacao],
) -> dict[tuple[int, int], dict]:
    venda_ids = {
        int(mov.referencia_id)
        for mov in movimentacoes
        if mov.referencia_id
        and (
            str(mov.referencia_tipo or "").lower() == "venda"
            or str(mov.motivo or "").lower() == "venda"
        )
    }
    produto_ids = {int(mov.produto_id) for mov in movimentacoes if mov.produto_id}
    if not venda_ids or not produto_ids:
        return {}

    itens = db.query(VendaItem).options(
        joinedload(VendaItem.produto),
        joinedload(VendaItem.venda),
    ).join(Venda, Venda.id == VendaItem.venda_id).filter(
        Venda.tenant_id == tenant_id,
        VendaItem.tenant_id == tenant_id,
        VendaItem.venda_id.in_(venda_ids),
        VendaItem.produto_id.in_(produto_ids),
    ).all()

    mapa = {}
    for item in itens:
        chave = (int(item.venda_id), int(item.produto_id))
        info = _detectar_promocao_venda_item(item)
        atual = mapa.get(chave)
        if not atual:
            mapa[chave] = info
            continue

        if info.get("em_promocao"):
            motivos = [
                parte.strip()
                for parte in f"{atual.get('promocao_origem') or ''}, {info.get('promocao_origem') or ''}".split(",")
                if parte.strip()
            ]
            atual.update(
                {
                    "em_promocao": True,
                    "promocao_origem": ", ".join(list(dict.fromkeys(motivos))),
                    "valor_promocional": round(
                        float(atual.get("valor_promocional", 0) or 0)
                        + float(info.get("valor_promocional", 0) or 0),
                        2,
                    ),
                    "desconto_promocional": round(
                        float(atual.get("desconto_promocional", 0) or 0)
                        + float(info.get("desconto_promocional", 0) or 0),
                        2,
                    ),
                }
            )

    return mapa


def _serializar_movimentacao_relatorio(
    mov: EstoqueMovimentacao,
    promocao_info: Optional[dict] = None,
) -> dict:
    produto = mov.produto
    motivo = (mov.motivo or "").strip()
    promocao_info = promocao_info or {}

    return {
        "id": mov.id,
        "data": mov.created_at.strftime("%d/%m/%Y") if mov.created_at else None,
        "data_completa": mov.created_at.isoformat() if mov.created_at else None,
        "codigo": produto.codigo if produto else "N/A",
        "sku": _produto_sku_value(produto) if produto else None,
        "codigo_barras": produto.codigo_barras if produto else None,
        "produto_nome": produto.nome if produto else "Produto removido",
        "produto_id": mov.produto_id,
        "entrada": float(mov.quantidade or 0) if mov.tipo == "entrada" else None,
        "saida": float(mov.quantidade or 0) if mov.tipo != "entrada" else None,
        "estoque": float(mov.quantidade_nova or 0),
        "tipo": (mov.tipo or "").title(),
        "motivo": motivo,
        "motivo_label": motivo.replace("_", " ").title() if motivo else None,
        "valor_unitario": float(mov.custo_unitario or 0),
        "valor_total": float(mov.valor_total or 0),
        "usuario": mov.user.nome if mov.user else "Sistema",
        "numero_pedido": mov.documento,
        "lancamento": mov.created_at.strftime("%d/%m/%Y %H:%M:%S") if mov.created_at else None,
        "observacoes": mov.observacao,
        "lotes_consumidos": mov.lotes_consumidos,
        "em_promocao": bool(promocao_info.get("em_promocao")),
        "promocao_origem": promocao_info.get("promocao_origem"),
        "preco_cadastro": promocao_info.get("preco_cadastro"),
        "preco_promocional_cadastro": promocao_info.get("preco_promocional_cadastro"),
        "desconto_promocional": promocao_info.get("desconto_promocional", 0),
        "valor_promocional": promocao_info.get("valor_promocional", 0),
    }
