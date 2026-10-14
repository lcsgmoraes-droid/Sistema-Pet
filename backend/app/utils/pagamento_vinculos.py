"""Vinculos de pagamentos nos campos de referencia ja existentes (sem migration)."""

import re

_MARCADOR = re.compile(r"\[venda_pagamento:(\d+)\]")


def referencia_pagamento(pagamento_id):
    return f"PAGAMENTO-{int(pagamento_id)}"


def marcar_pagamento(texto, pagamento_id):
    if pagamento_id is None:
        return texto
    marcador = f"[venda_pagamento:{int(pagamento_id)}]"
    return f"{texto or ''} {marcador}".strip()


def pagamento_da_observacao(texto):
    encontrados = _MARCADOR.findall(texto or "")
    return int(encontrados[0]) if len(encontrados) == 1 else None
