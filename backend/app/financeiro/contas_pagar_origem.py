from __future__ import annotations

import re
from typing import Any, Optional

CAIXA_PDV_OBSERVACAO_MARKER = "Gerada automaticamente pelo PDV"


def _extrair_caixa_referencia(observacoes: Optional[str]) -> Optional[str]:
    match = re.search(r"Caixa\s+#?([0-9]+)", observacoes or "", re.IGNORECASE)
    if not match:
        return None
    return f"Caixa #{match.group(1)}"


def _identificar_origem_conta_pagar(conta: Any) -> dict:
    observacoes = conta.observacoes or ""
    if CAIXA_PDV_OBSERVACAO_MARKER.lower() in observacoes.lower():
        caixa_ref = _extrair_caixa_referencia(observacoes)
        return {
            "origem_lancamento": "caixa_pdv",
            "origem_lancamento_label": "Caixa/PDV",
            "caixa_referencia": caixa_ref,
        }

    if conta.nota_entrada_id:
        return {
            "origem_lancamento": "nota_entrada",
            "origem_lancamento_label": "Nota de entrada",
            "caixa_referencia": None,
        }

    return {
        "origem_lancamento": "manual",
        "origem_lancamento_label": "Manual/financeiro",
        "caixa_referencia": None,
    }
