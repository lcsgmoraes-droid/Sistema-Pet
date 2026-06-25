"""Constantes e helpers compartilhados da baixa FULL por NF."""

_CANAL_LABELS = {
    "full": "FULL (geral)",
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
    "site": "Site",
    "app": "App",
    "whatsapp": "WhatsApp",
    "bling": "Bling",
    "online": "Online",
    "loja_fisica": "Loja Fisica",
    "transferencia_parceiro": "Transferencia Parceiro",
}


def _texto_limpo(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None
