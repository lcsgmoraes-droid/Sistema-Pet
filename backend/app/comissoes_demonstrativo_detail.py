from typing import Any, Dict

from app.comissoes_demonstrativo_calculo import (
    campanha_item_do_snapshot,
    decimal_to_float,
    montar_demonstrativo_calculo_comissao,
    round_money,
)


def montar_detalhe_comissao_snapshot(r: Any) -> Dict[str, Any]:
    """Monta o payload de detalhe sem recalcular a comissao salva."""
    valor_venda = decimal_to_float(r["valor_venda"]) or 0.0
    valor_base_calculo = decimal_to_float(r["valor_base_calculo"]) or 0.0
    quantidade_item = (
        decimal_to_float(r.get("item_quantidade"))
        or decimal_to_float(r["quantidade"])
        or 0.0
    )
    preco_unitario_item = (
        decimal_to_float(r.get("item_preco_unitario"))
        if r.get("item_preco_unitario") is not None
        else None
    )
    valor_bruto_item = (
        round_money(preco_unitario_item * quantidade_item)
        if preco_unitario_item is not None and quantidade_item
        else round_money(valor_venda)
    )
    desconto_total_item = max(round_money(valor_bruto_item - valor_venda), 0.0)
    beneficio_item = campanha_item_do_snapshot(
        r.get("rentabilidade_snapshot"), r.get("produto_id")
    )
    if (
        beneficio_item <= 0
        and r.get("cupom_discount_applied")
        and r.get("desconto_total_venda")
    ):
        desconto_total_venda = decimal_to_float(r.get("desconto_total_venda"))
        cupom_total = decimal_to_float(r.get("cupom_discount_applied"))
        if desconto_total_venda > 0:
            beneficio_item = round_money(
                desconto_total_item * min(cupom_total / desconto_total_venda, 1.0)
            )
    beneficio_item = min(beneficio_item, desconto_total_item)
    desconto_manual_item = max(round_money(desconto_total_item - beneficio_item), 0.0)

    demonstrativo_calculo = montar_demonstrativo_calculo_comissao(
        tipo_calculo=r["tipo_calculo"],
        valor_bruto=valor_bruto_item,
        desconto=desconto_manual_item,
        beneficio=beneficio_item,
        taxa_cartao=r.get("taxa_cartao_item") or 0,
        imposto=r.get("impostos_item") or 0,
        taxa_entregador=r.get("taxa_entregador_item") or 0,
        custo_operacional=r.get("custo_operacional_item") or 0,
        receita_taxa_entrega=r.get("receita_taxa_entrega_item") or 0,
        custo_produto=r["valor_custo"] or 0,
        valor_base_calculo=valor_base_calculo,
        percentual_comissao=r["percentual_comissao"],
        valor_comissao=r["valor_comissao"],
        valor_comissao_gerada=r["valor_comissao_gerada"],
        percentual_aplicado=r["percentual_aplicado"],
    )
    deducoes_aplicadas = sum(
        linha["valor"]
        for linha in demonstrativo_calculo["linhas"]
        if linha["operador"] == "-" and linha["entra_na_base"]
    )

    return {
        "id": r["id"],
        "venda_id": r["venda_id"],
        "numero_venda": r["numero_venda"],
        "total_venda": decimal_to_float(r["total_venda"]),
        "data_venda": str(r["data_venda"]) if r["data_venda"] else None,
        "funcionario_id": r["funcionario_id"],
        "produto_id": r["produto_id"],
        "venda_item_id": r["venda_item_id"],
        "quantidade": decimal_to_float(r["quantidade"]),
        "parcela_numero": r["parcela_numero"],
        "valores_financeiros": {
            "valor_venda": valor_venda,
            "valor_custo": decimal_to_float(r["valor_custo"]),
            "valor_base_original": decimal_to_float(r["valor_base_original"]),
            "valor_base_comissionada": decimal_to_float(r["valor_base_comissionada"]),
        },
        "origem_base_calculo": {
            "valor_inicial": valor_bruto_item,
            "deducoes_aplicadas": round_money(deducoes_aplicadas),
            "valor_final": valor_base_calculo,
            "explicacao": demonstrativo_calculo["formula_resumo"],
        },
        "demonstrativo_calculo": demonstrativo_calculo,
        "deducoes": {
            "valor_bruto": valor_bruto_item,
            "desconto": desconto_manual_item,
            "beneficio": beneficio_item,
            "taxa_cartao": (
                decimal_to_float(r.get("taxa_cartao_item"))
                if r.get("taxa_cartao_item")
                else 0.0
            ),
            "imposto": (
                decimal_to_float(r.get("impostos_item"))
                if r.get("impostos_item")
                else 0.0
            ),
            "taxa_entregador": (
                decimal_to_float(r.get("taxa_entregador_item"))
                if r.get("taxa_entregador_item")
                else 0.0
            ),
            "custo_operacional": (
                decimal_to_float(r.get("custo_operacional_item"))
                if r.get("custo_operacional_item")
                else 0.0
            ),
            "receita_taxa_entrega": (
                decimal_to_float(r.get("receita_taxa_entrega_item"))
                if r.get("receita_taxa_entrega_item")
                else 0.0
            ),
            "percentual_impostos": (
                decimal_to_float(r.get("percentual_impostos"))
                if r.get("percentual_impostos")
                else 0.0
            ),
            "forma_pagamento": r.get("forma_pagamento"),
            "numero_parcelas": r.get("numero_parcelas"),
            "taxa_percentual": (
                decimal_to_float(r.get("taxa_percentual"))
                if r.get("taxa_percentual")
                else None
            ),
            "taxas_por_parcela": r.get("taxas_por_parcela"),
        },
        "calculo": {
            "tipo_calculo": r["tipo_calculo"],
            "valor_base_calculo": valor_base_calculo,
            "percentual_comissao": decimal_to_float(r["percentual_comissao"]),
            "percentual_aplicado": decimal_to_float(r["percentual_aplicado"]),
            "valor_comissao": decimal_to_float(r["valor_comissao"]),
            "valor_comissao_gerada": decimal_to_float(r["valor_comissao_gerada"]),
        },
        "pagamento": {
            "percentual_pago": decimal_to_float(r["percentual_pago"]),
            "valor_pago_referencia": decimal_to_float(r["valor_pago_referencia"]),
            "valor_pago": decimal_to_float(r["valor_pago"]),
            "saldo_restante": decimal_to_float(r["saldo_restante"]),
            "data_pagamento": str(r["data_pagamento"]) if r["data_pagamento"] else None,
            "forma_pagamento": r["forma_pagamento"],
        },
        "status": {
            "status": r["status"],
            "data_estorno": str(r["data_estorno"]) if r["data_estorno"] else None,
            "motivo_estorno": r["motivo_estorno"],
            "observacao_pagamento": r["observacao_pagamento"],
        },
    }
