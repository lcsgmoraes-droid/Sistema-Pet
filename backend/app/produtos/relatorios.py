"""Helpers de relatorios de produtos e movimentacoes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.promocoes_venda_utils import detectar_promocao_por_preco_vendido
from app.produtos.core import _produto_sku_value
from app.produtos_models import EstoqueMovimentacao
from app.vendas_models import Venda, VendaItem


def _parse_relatorio_datetime(
    valor: Optional[str], *, end_of_day: bool = False
) -> Optional[datetime]:
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


def _calcular_janelas_vendas_produto(
    analise_rows,
    *,
    data_fim_dt: datetime,
    janela_30_inicio: datetime,
) -> tuple[dict[str, dict], list[dict]]:
    janelas = {}
    vendas_por_janela = {}
    for dias in (7, 15, 30, 60, 90):
        chave = str(dias)
        janelas[chave] = {
            "dias": dias,
            "quantidade_vendida": 0.0,
            "valor_vendido": 0.0,
            "numero_vendas": 0,
            "media_diaria": 0.0,
        }
        vendas_por_janela[chave] = set()

    curva_30_map = {}
    for deslocamento in range(30):
        data_ref = (janela_30_inicio + timedelta(days=deslocamento)).date().isoformat()
        curva_30_map[data_ref] = 0.0

    for row in analise_rows:
        quantidade = float(row.quantidade or 0)
        subtotal = float(row.subtotal or 0)
        diferenca_dias = max(0, (data_fim_dt.date() - row.data_venda.date()).days)
        data_ref = row.data_venda.date().isoformat()

        if data_ref in curva_30_map:
            curva_30_map[data_ref] += quantidade

        for dias in (7, 15, 30, 60, 90):
            if diferenca_dias < dias:
                chave = str(dias)
                janelas[chave]["quantidade_vendida"] += quantidade
                janelas[chave]["valor_vendido"] += subtotal
                vendas_por_janela[chave].add(row.venda_id)

    for dias in (7, 15, 30, 60, 90):
        chave = str(dias)
        janelas[chave]["numero_vendas"] = len(vendas_por_janela[chave])
        janelas[chave]["quantidade_vendida"] = round(
            janelas[chave]["quantidade_vendida"], 3
        )
        janelas[chave]["valor_vendido"] = round(janelas[chave]["valor_vendido"], 2)
        janelas[chave]["media_diaria"] = round(
            janelas[chave]["quantidade_vendida"] / dias if dias else 0,
            2,
        )

    curva_30_dias = [
        {
            "data": data_ref,
            "quantidade": round(float(quantidade or 0), 3),
        }
        for data_ref, quantidade in sorted(curva_30_map.items())
    ]

    return janelas, curva_30_dias


def _calcular_totais_validade_proxima(
    resumo_rows,
    *,
    agora: datetime,
    campaign_configs: dict,
    exclusoes_produto: dict,
    exclusoes_lote: dict,
) -> dict:
    totais = {
        "total_lotes": len(resumo_rows),
        "total_produtos": len({row[1] for row in resumo_rows}),
        "total_quantidade": 0.0,
        "lotes_vencidos": 0,
        "lotes_ate_7_dias": 0,
        "lotes_ate_30_dias": 0,
        "lotes_ate_60_dias": 0,
        "valor_custo_em_risco": 0.0,
        "valor_venda_em_risco": 0.0,
        "lotes_em_campanha": 0,
        "lotes_excluidos_campanha": 0,
    }

    for (
        lote_id,
        produto_id,
        tenant_row_id,
        data_validade_item,
        quantidade_item,
        custo_item,
        venda_item,
    ) in resumo_rows:
        quantidade = float(quantidade_item or 0)
        custo = float(custo_item or 0)
        venda = float(venda_item or 0)
        dias_item = (data_validade_item - agora).days if data_validade_item else None
        tenant_key = str(tenant_row_id)
        config = campaign_configs.get(tenant_key)
        exclusao_produto = exclusoes_produto.get((tenant_key, int(produto_id)))
        exclusao_lote = exclusoes_lote.get((tenant_key, int(lote_id)))

        totais["total_quantidade"] += quantidade
        totais["valor_custo_em_risco"] += quantidade * custo
        totais["valor_venda_em_risco"] += quantidade * venda

        if exclusao_produto or exclusao_lote:
            totais["lotes_excluidos_campanha"] += 1
        elif (
            quantidade > 0
            and config
            and bool(config.ativo)
            and (bool(config.aplicar_app) or bool(config.aplicar_ecommerce))
            and dias_item is not None
            and dias_item >= 0
            and (
                (dias_item <= 7 and float(config.desconto_7_dias or 0) > 0)
                or (dias_item <= 30 and float(config.desconto_30_dias or 0) > 0)
                or (dias_item <= 60 and float(config.desconto_60_dias or 0) > 0)
            )
        ):
            totais["lotes_em_campanha"] += 1

        if dias_item is None:
            continue
        if dias_item < 0:
            totais["lotes_vencidos"] += 1
            continue
        if dias_item <= 7:
            totais["lotes_ate_7_dias"] += 1
        if dias_item <= 30:
            totais["lotes_ate_30_dias"] += 1
        if dias_item <= 60:
            totais["lotes_ate_60_dias"] += 1

    return totais


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

    itens = (
        db.query(VendaItem)
        .options(
            joinedload(VendaItem.produto),
            joinedload(VendaItem.venda),
        )
        .join(Venda, Venda.id == VendaItem.venda_id)
        .filter(
            Venda.tenant_id == tenant_id,
            VendaItem.tenant_id == tenant_id,
            VendaItem.venda_id.in_(venda_ids),
            VendaItem.produto_id.in_(produto_ids),
        )
        .all()
    )

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
                for parte in f"{atual.get('promocao_origem') or ''}, {info.get('promocao_origem') or ''}".split(
                    ","
                )
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
        "lancamento": mov.created_at.strftime("%d/%m/%Y %H:%M:%S")
        if mov.created_at
        else None,
        "observacoes": mov.observacao,
        "lotes_consumidos": mov.lotes_consumidos,
        "em_promocao": bool(promocao_info.get("em_promocao")),
        "promocao_origem": promocao_info.get("promocao_origem"),
        "preco_cadastro": promocao_info.get("preco_cadastro"),
        "preco_promocional_cadastro": promocao_info.get("preco_promocional_cadastro"),
        "desconto_promocional": promocao_info.get("desconto_promocional", 0),
        "valor_promocional": promocao_info.get("valor_promocional", 0),
    }
