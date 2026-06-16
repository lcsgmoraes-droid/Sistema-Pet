"""
Exemplos de calculo completo de margem com todos os custos.

O script chama o endpoint local de analise de venda e mostra quatro cenarios:
- venda simples sem entrega
- venda com entrega
- venda completa com taxa, desconto e comissao
- venda com margem baixa
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests


API_URL = "http://localhost:8000"
TOKEN = "seu_token_aqui"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


def analisar_venda(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    response = requests.post(
        f"{API_URL}/pdv/indicadores/analisar-venda",
        json=dict(payload),
        headers=HEADERS,
        timeout=30,
    )

    if response.status_code != 200:
        print(f"Erro: {response.status_code} - {response.text}")
        return None

    return response.json()


def print_resultado(payload: Mapping[str, Any], resultado: Mapping[str, Any]) -> None:
    print("\nREQUEST:")
    print(f"   Subtotal: R$ {payload['subtotal']:.2f}")
    print(f"   Custo produtos: R$ {payload['custo_total']:.2f}")
    print(f"   Desconto: R$ {payload.get('desconto', 0):.2f}")

    if payload.get("taxa_entrega", 0) > 0:
        print(f"   Taxa entrega: R$ {payload['taxa_entrega']:.2f}")
        print(f"   Custo entrega: R$ {payload['custo_operacional_entrega']:.2f}")

    if payload.get("comissao_percentual", 0) > 0:
        print(f"   Comissao: {payload['comissao_percentual']}%")

    valores = resultado["valores"]
    margens = resultado["margens"]
    status = resultado["status"]

    print("\nRESPONSE:")
    print(f"   Total venda: R$ {valores['total_venda']:.2f}")
    print(f"   Margem bruta: {margens['margem_bruta_percentual']:.1f}%")
    print(f"   Margem liquida: {margens['margem_liquida_percentual']:.1f}%")
    print(f"   Lucro liquido: R$ {margens['lucro_liquido']:.2f}")
    print(f"   Status: {status['icone']} {status['status'].upper()}")


def executar_exemplo(titulo: str, payload: Mapping[str, Any]) -> dict[str, Any] | None:
    print("\n" + "=" * 60)
    print(titulo)
    print("=" * 60)

    resultado = analisar_venda(payload)
    if resultado is not None:
        print_resultado(payload, resultado)
    return resultado


def exemplo_venda_simples() -> None:
    executar_exemplo(
        "EXEMPLO 1: Venda simples no balcao",
        {
            "subtotal": 100.00,
            "custo_total": 60.00,
            "desconto": 0,
            "forma_pagamento_id": 1,
            "parcelas": 1,
            "taxa_entrega": 0,
            "custo_operacional_entrega": 0,
            "comissao_percentual": 0,
            "comissao_valor": 0,
        },
    )


def exemplo_venda_com_entrega() -> None:
    executar_exemplo(
        "EXEMPLO 2: Venda com entrega",
        {
            "subtotal": 100.00,
            "custo_total": 60.00,
            "desconto": 5.00,
            "forma_pagamento_id": 2,
            "parcelas": 1,
            "taxa_entrega": 15.00,
            "custo_operacional_entrega": 8.00,
            "comissao_percentual": 0,
            "comissao_valor": 0,
        },
    )


def exemplo_venda_completa() -> None:
    resultado = executar_exemplo(
        "EXEMPLO 3: Venda completa com todos os custos",
        {
            "subtotal": 250.00,
            "custo_total": 140.00,
            "desconto": 10.00,
            "forma_pagamento_id": 3,
            "parcelas": 3,
            "taxa_entrega": 20.00,
            "custo_operacional_entrega": 9.00,
            "comissao_percentual": 2.0,
            "comissao_valor": 0,
        },
    )

    if resultado is None:
        return

    valores = resultado["valores"]
    custos = resultado["custos"]
    margens = resultado["margens"]
    resultado_entrega = (
        valores.get("taxa_entrega_receita_empresa", 0)
        - custos.get("custo_operacional_entrega", 0)
    )

    print("\nANALISE DETALHADA:")
    print(f"   Total: R$ {valores['total_venda']:.2f}")
    print(f"   Custo produtos: R$ {custos['custo_produtos']:.2f}")
    print(f"   Taxa pagamento: R$ {custos['taxa_pagamento']:.2f}")
    print(f"   Impostos: R$ {custos['imposto']:.2f}")
    print(f"   Comissao vendedor: R$ {custos['comissao_vendedor']:.2f}")
    print(f"   Lucro liquido: R$ {margens['lucro_liquido']:.2f}")
    print(f"   Resultado entrega empresa: R$ {resultado_entrega:.2f}")


def exemplo_venda_margem_baixa() -> None:
    resultado = executar_exemplo(
        "EXEMPLO 4: Venda com margem baixa",
        {
            "subtotal": 100.00,
            "custo_total": 75.00,
            "desconto": 5.00,
            "forma_pagamento_id": 4,
            "parcelas": 12,
            "taxa_entrega": 10.00,
            "custo_operacional_entrega": 8.00,
            "comissao_percentual": 3.0,
            "comissao_valor": 0,
        },
    )

    if resultado is None:
        return

    margens = resultado["margens"]
    print("\nALERTA:")
    print(
        "   Esta venda tem margem liquida de "
        f"{margens['margem_liquida_percentual']:.1f}%"
    )
    print(f"   Lucro liquido: R$ {margens['lucro_liquido']:.2f}")
    print("   Considere reduzir desconto, parcelas ou comissoes.")


if __name__ == "__main__":
    print("Exemplos de calculo de margem com todos os custos")
    exemplo_venda_simples()
    exemplo_venda_com_entrega()
    exemplo_venda_completa()
    exemplo_venda_margem_baixa()
    print("\nExemplos executados.")
