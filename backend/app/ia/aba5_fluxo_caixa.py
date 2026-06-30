"""
ABA 5: Fluxo de Caixa Preditivo.

Este modulo permanece como fachada publica. A implementacao fica em
app.ia.aba5_fluxo_caixa_parts para manter os contratos antigos de importacao.
"""

import logging

from app.ia.aba5_fluxo_caixa_parts import (
    PROPHET_AVAILABLE,
    _gerar_projecoes_estaticas,
    _get_user_tenant_id,
    _montar_projecoes_estaticas,
    _persistir_projecoes_estaticas,
    _resolve_tenant_id,
    _saldo_realizado_atual,
    _utcnow_naive,
    calcular_indices_saude,
    gerar_alertas_caixa,
    obter_projecoes_proximos_dias,
    projetar_fluxo_15_dias,
    registrar_movimentacao,
    simular_cenario,
)

logger = logging.getLogger(__name__)

__all__ = [
    "_get_user_tenant_id",
    "_resolve_tenant_id",
    "_utcnow_naive",
    "_saldo_realizado_atual",
    "_montar_projecoes_estaticas",
    "_persistir_projecoes_estaticas",
    "_gerar_projecoes_estaticas",
    "PROPHET_AVAILABLE",
    "calcular_indices_saude",
    "projetar_fluxo_15_dias",
    "obter_projecoes_proximos_dias",
    "simular_cenario",
    "gerar_alertas_caixa",
    "registrar_movimentacao",
]


if __name__ == "__main__":
    logger.info("Modulo ABA 5 - Fluxo de Caixa Preditivo")
    logger.info("Funcoes disponiveis:")
    for nome in __all__:
        if not nome.startswith("_") and nome != "PROPHET_AVAILABLE":
            logger.info("  %s()", nome)
