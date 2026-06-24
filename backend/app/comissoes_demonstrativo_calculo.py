from decimal import Decimal
from typing import Any, Dict, Optional


def decimal_to_float(value: Any) -> float:
    """Converte Decimal para float de forma segura."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def round_money(value: Any) -> float:
    return round(decimal_to_float(value), 2)


def montar_demonstrativo_calculo_comissao(
    *,
    tipo_calculo: str,
    valor_bruto: Any,
    desconto: Any,
    beneficio: Any,
    taxa_cartao: Any,
    imposto: Any,
    taxa_entregador: Any,
    custo_operacional: Any,
    receita_taxa_entrega: Any,
    custo_produto: Any,
    valor_base_calculo: Any,
    percentual_comissao: Any,
    valor_comissao: Any,
    valor_comissao_gerada: Any,
    percentual_aplicado: Any,
) -> Dict[str, Any]:
    """Monta o extrato da comissao sem recalcular o valor salvo."""
    tipo_normalizado = (tipo_calculo or "percentual").lower()
    desconto = round_money(desconto)
    beneficio = round_money(beneficio)
    taxa_cartao = round_money(taxa_cartao)
    imposto = round_money(imposto)
    taxa_entregador = round_money(taxa_entregador)
    custo_operacional = round_money(custo_operacional)
    receita_taxa_entrega = round_money(receita_taxa_entrega)
    custo_produto = round_money(custo_produto)
    valor_bruto = round_money(valor_bruto)
    valor_base_calculo = round_money(valor_base_calculo)
    percentual_comissao = round_money(percentual_comissao)
    valor_comissao = round_money(valor_comissao)
    valor_comissao_gerada = round_money(valor_comissao_gerada)
    percentual_aplicado = round_money(percentual_aplicado)

    inclui_custo_produto = tipo_normalizado == "lucro"
    lucro_conferido = round_money(
        valor_bruto
        + receita_taxa_entrega
        - desconto
        - beneficio
        - taxa_cartao
        - imposto
        - taxa_entregador
        - custo_operacional
        - (custo_produto if inclui_custo_produto else 0)
    )

    linhas = [
        {
            "chave": "preco_venda",
            "label": "Preco de venda bruto",
            "operador": "+",
            "tipo": "receita",
            "valor": valor_bruto,
            "entra_na_base": True,
        },
        {
            "chave": "desconto",
            "label": "Desconto comercial",
            "operador": "-",
            "tipo": "deducao",
            "valor": desconto,
            "entra_na_base": True,
        },
        {
            "chave": "beneficio",
            "label": "Beneficio / cupom / cashback",
            "operador": "-",
            "tipo": "deducao",
            "valor": beneficio,
            "entra_na_base": True,
        },
        {
            "chave": "receita_taxa_entrega",
            "label": "Taxa de entrega recebida",
            "operador": "+",
            "tipo": "receita",
            "valor": receita_taxa_entrega,
            "entra_na_base": True,
        },
        {
            "chave": "taxa_cartao",
            "label": "Taxa de cartao / meio de pagamento",
            "operador": "-",
            "tipo": "deducao",
            "valor": taxa_cartao,
            "entra_na_base": True,
        },
        {
            "chave": "imposto",
            "label": "Impostos",
            "operador": "-",
            "tipo": "deducao",
            "valor": imposto,
            "entra_na_base": True,
        },
        {
            "chave": "taxa_entregador",
            "label": "Entrega - repasse ao entregador",
            "operador": "-",
            "tipo": "deducao",
            "valor": taxa_entregador,
            "entra_na_base": True,
        },
        {
            "chave": "custo_operacional_entrega",
            "label": "Entrega - custo operacional",
            "operador": "-",
            "tipo": "deducao",
            "valor": custo_operacional,
            "entra_na_base": True,
        },
        {
            "chave": "custo_produto",
            "label": "Custo do produto vendido",
            "operador": "-" if inclui_custo_produto else "i",
            "tipo": "deducao" if inclui_custo_produto else "informativo",
            "valor": custo_produto,
            "entra_na_base": inclui_custo_produto,
        },
        {
            "chave": "base_calculo",
            "label": (
                "Lucro comissionavel" if inclui_custo_produto else "Base comissionavel"
            ),
            "operador": "=",
            "tipo": "resultado",
            "valor": valor_base_calculo,
            "entra_na_base": False,
        },
        {
            "chave": "percentual_comissao",
            "label": "Percentual da comissao",
            "operador": "x",
            "tipo": "percentual",
            "valor": percentual_comissao,
            "entra_na_base": False,
        },
        {
            "chave": "comissao_total",
            "label": "Comissao calculada",
            "operador": "=",
            "tipo": "resultado",
            "valor": valor_comissao,
            "entra_na_base": False,
        },
        {
            "chave": "percentual_aplicado",
            "label": "Percentual pago da venda",
            "operador": "x",
            "tipo": "percentual",
            "valor": percentual_aplicado,
            "entra_na_base": False,
        },
        {
            "chave": "comissao_final",
            "label": "Comissao gerada para pagamento",
            "operador": "=",
            "tipo": "final",
            "valor": valor_comissao_gerada,
            "entra_na_base": False,
        },
    ]

    formula_resumo = (
        "preco_venda - desconto - beneficio - taxas - impostos - entrega - custo_produto = lucro_comissionavel"
        if inclui_custo_produto
        else "preco_venda - desconto - beneficio - taxas - impostos - entrega = base_comissionavel"
    )

    return {
        "tipo_calculo": tipo_normalizado,
        "formula_resumo": formula_resumo,
        "linhas": linhas,
        "lucro_conferido": lucro_conferido,
        "conferencia_ok": abs(lucro_conferido - valor_base_calculo) <= 0.05,
        "observacao": (
            "Comissao sobre lucro: o custo do produto entra como deducao da base."
            if inclui_custo_produto
            else "Comissao percentual: o custo do produto aparece como informativo, sem deduzir a base."
        ),
    }


def campanha_item_do_snapshot(snapshot: Any, produto_id: Optional[int]) -> float:
    if not isinstance(snapshot, dict) or produto_id is None:
        return 0.0

    for item in snapshot.get("itens") or []:
        try:
            if int(item.get("produto_id") or 0) == int(produto_id):
                return round_money(item.get("campanha", 0))
        except (TypeError, ValueError):
            continue
    return 0.0
