from __future__ import annotations


def stone_template_mapping(
    *, parcela_key: str, parcela_transformacao: str
) -> dict[str, dict[str, object]]:
    return {
        "nsu": {"coluna": "STONE ID", "transformacao": "nsu", "obrigatorio": True},
        "data_venda": {
            "coluna": "DATA DA VENDA",
            "transformacao": "data_br",
            "obrigatorio": True,
        },
        "data_pagamento": {
            "coluna": "DATA DO ULTIMO STATUS",
            "transformacao": "data_br",
            "obrigatorio": False,
        },
        "valor_bruto": {
            "coluna": "VALOR BRUTO",
            "transformacao": "monetario_br",
            "obrigatorio": True,
        },
        "taxa_mdr": {
            "coluna": "DESCONTO DE MDR",
            "transformacao": "monetario_br",
            "obrigatorio": False,
        },
        "valor_taxa": {
            "coluna": "DESCONTO UNIFICADO",
            "transformacao": "monetario_br",
            "obrigatorio": False,
        },
        "valor_liquido": {
            "coluna": "VALOR LIQUIDO",
            "transformacao": "monetario_br",
            "obrigatorio": True,
        },
        parcela_key: {
            "coluna": "N DE PARCELAS",
            "transformacao": parcela_transformacao,
            "obrigatorio": False,
        },
        "tipo_transacao": {
            "coluna": "PRODUTO",
            "transformacao": "texto",
            "obrigatorio": False,
        },
        "bandeira": {
            "coluna": "BANDEIRA",
            "transformacao": "texto",
            "obrigatorio": False,
        },
    }
