"""Leituras em lote para aplicar Financial sem refazer a operacao da venda."""

from app.services.rentabilidade_pendencias import venda_aguarda_financial_ifood
from app.config import settings


def _vendas_ifood(vendas):
    return [
        venda
        for venda in vendas
        if venda_aguarda_financial_ifood(venda)
        and isinstance(getattr(venda, "id", None), int)
        and not isinstance(venda.id, bool)
        and venda.id > 0
    ]


def carregar_financial_das_vendas(db, tenant_id, vendas):
    selecionadas = _vendas_ifood(vendas)
    if not selecionadas:
        return {}
    from app.integrations.ifood.sale_financials import resolve_sales_financials

    return resolve_sales_financials(
        db,
        tenant_id,
        [venda.id for venda in selecionadas],
        allow_synthetic=bool(
            getattr(settings, "IFOOD_FINANCIAL_SHOW_SYNTHETIC", False)
        ),
    )


def carregar_snapshots_ifood_vendas(db, tenant_id, vendas):
    """Reutiliza o CMV congelado ou os comprovantes locais, sem gravar snapshot."""
    selecionadas = _vendas_ifood(vendas)
    if not selecionadas:
        return {}
    from app.relatorio_vendas_common import _valor_cupom_venda
    from app.relatorio_vendas_preloads import carregar_contexto_relatorio_vendas
    from app.services.venda_rentabilidade_snapshot_service import (
        get_or_build_venda_rentabilidade_snapshot,
    )

    financeiros = carregar_financial_das_vendas(db, tenant_id, selecionadas)
    contexto = carregar_contexto_relatorio_vendas(
        db=db, tenant_id=tenant_id, vendas=selecionadas
    )
    resultado = {}
    for venda in selecionadas:
        cupom = _valor_cupom_venda(venda, contexto["cupons_por_venda"])
        campanha = cupom + contexto["cashback_por_venda"].get(venda.id, 0.0)
        resultado[venda.id] = get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=False,
            ifood_financial=financeiros.get(venda.id, {}),
            impostos_percentual=contexto["impostos_percentual_global"],
            formas_pagamento_map=contexto["formas_pagamento_map"],
            custo_campanha=campanha,
            cupom_desconto=cupom,
            comissao_total=contexto["comissao_total_por_venda"].get(venda.id, 0.0),
            taxa_operacional_entrega=(
                contexto["entregadores_map"].get(venda.entregador_id, 0.0)
                if getattr(venda, "tem_entrega", False)
                else 0.0
            ),
            estoque_custos_por_produto=contexto["estoque_custos_por_venda"].get(
                venda.id, {}
            ),
        )
    return resultado
