"""Integracao publica com a API Bling v3."""

from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from app.bling_integration_fiscal import (
    aplicar_correcoes_fiscais_venda,
    prevalidar_fiscal_venda,
)
from app.bling_integration_parts.api import BlingAPI
from app.bling_integration_parts.core import (
    BLING_API_BASE_URL,
    BLING_NFCE_SERIE_PADRAO,
    BLING_NFE_SERIE_PADRAO,
    ENV_PATHS,
    TOKEN_CONTROL_FILE,
    _aguardar_slot_bling,
    _erro_rate_limit_bling,
    _get_shared_env_path,
    _load_bling_runtime_config,
    _montar_url_bling,
    _tempo_espera_rate_limit_bling,
)

__all__ = [
    "BLING_API_BASE_URL",
    "BLING_NFCE_SERIE_PADRAO",
    "BLING_NFE_SERIE_PADRAO",
    "BlingAPI",
    "ENV_PATHS",
    "TOKEN_CONTROL_FILE",
    "_aguardar_slot_bling",
    "_erro_rate_limit_bling",
    "_get_shared_env_path",
    "_load_bling_runtime_config",
    "_montar_url_bling",
    "_tempo_espera_rate_limit_bling",
    "aplicar_correcoes_fiscais_venda",
    "emitir_nfe_venda",
    "prevalidar_fiscal_venda",
]


def emitir_nfe_venda(venda_id: int, tipo_nota: str, db: Session) -> Dict:
    """Funcao auxiliar para emitir NF-e de uma venda."""
    from app.vendas_models import Venda

    venda = db.query(Venda).filter(Venda.id == venda_id).first()
    if not venda:
        raise ValueError(f"Venda {venda_id} nao encontrada")

    bling = BlingAPI()
    return bling.emitir_nota_fiscal(venda, tipo_nota, db)
