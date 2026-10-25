"""Protege resultados enquanto as cobrancas iFood nao foram conciliadas.

Pagamento online, taxa de pagamento e previsao contratual nao comprovam o
conjunto das cobrancas do marketplace. A integracao Financial ainda nao publica
um fechamento canonico na rentabilidade da Venda; ate esse vinculo existir,
nenhum desses valores pode liberar uma margem final nos relatorios gerais.
Leitura pura: nao consulta o provedor e nao altera a fotografia salva.
"""

from typing import Any

PENDING_IFOOD_FINANCIAL = "pending_ifood_financial"
PENDENCIA_IFOOD = (
    "Aguardando a conciliacao das cobrancas do iFood para calcular lucro e margem."
)


def venda_aguarda_financial_ifood(venda: Any) -> bool:
    canal = str(getattr(venda, "canal", "") or "").strip().lower()
    if canal == "ifood":
        return True
    return any(
        str(getattr(pagamento, "gateway_provider", "") or "").strip().lower() == "ifood"
        for pagamento in list(getattr(venda, "pagamentos", []) or [])
    )


def aplicar_pendencia_ifood(venda: Any, snapshot: dict) -> dict:
    if not (
        venda_aguarda_financial_ifood(venda)
        or str(snapshot.get("gateway_provider") or "").strip().lower() == "ifood"
        or snapshot.get("taxas_ifood_pendentes")
    ):
        return snapshot

    metadados = {
        "rentabilidade_status": PENDING_IFOOD_FINANCIAL,
        "taxas_ifood_pendentes": True,
        "pendencias_rentabilidade": [PENDENCIA_IFOOD],
        "taxa_ifood": None,
    }
    protegido = {**snapshot, **metadados}
    for campo in (
        "taxa_cartao",
        "taxa_gateway",
        "valor_liquido_gateway",
        "venda_liquida",
        "lucro",
        "margem_sobre_venda",
        "margem_sobre_custo",
    ):
        protegido[campo] = None

    protegido["itens"] = []
    for item in list(snapshot.get("itens") or []):
        copia = {**item, **metadados}
        for campo in (
            "taxa_cartao",
            "valor_liquido",
            "lucro",
            "lucro_unitario",
            "margem_sobre_venda",
            "margem_sobre_custo",
        ):
            copia[campo] = None
        protegido["itens"].append(copia)
    return protegido
