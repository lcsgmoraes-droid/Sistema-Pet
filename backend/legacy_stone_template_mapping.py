from __future__ import annotations


def stone_template_mapping(
    *, parcela_key: str, parcela_transformacao: str
) -> dict[str, dict[str, object]]:
    fields = (
        ("nsu", "STONE ID", "nsu", True),
        ("data_venda", "DATA DA VENDA", "data_br", True),
        ("data_pagamento", "DATA DO ULTIMO STATUS", "data_br", False),
        ("valor_bruto", "VALOR BRUTO", "monetario_br", True),
        ("taxa_mdr", "DESCONTO DE MDR", "monetario_br", False),
        ("valor_taxa", "DESCONTO UNIFICADO", "monetario_br", False),
        ("valor_liquido", "VALOR LIQUIDO", "monetario_br", True),
        (parcela_key, "N DE PARCELAS", parcela_transformacao, False),
        ("tipo_transacao", "PRODUTO", "texto", False),
        ("bandeira", "BANDEIRA", "texto", False),
    )

    return {
        key: {
            "coluna": coluna,
            "transformacao": transformacao,
            "obrigatorio": obrigatorio,
        }
        for key, coluna, transformacao, obrigatorio in fields
    }
