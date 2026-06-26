"""Fachada de compatibilidade para servicos de comissoes."""

# ruff: noqa: F401

from app.comissoes_config_service import (
    _configuracao_row_to_dict,
    _require_tenant_id,
    buscar_configuracao_comissao,
    calcular_comissao_item,
)
from app.comissoes_geracao_service import gerar_comissoes_venda
