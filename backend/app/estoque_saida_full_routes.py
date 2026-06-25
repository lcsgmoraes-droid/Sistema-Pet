"""Fachada compativel das rotas de baixa FULL por NF."""

from .estoque_saida_full.common import _CANAL_LABELS, _texto_limpo
from .estoque_saida_full.financeiro import (
    _buscar_conta_tarifa_full_nf,
    _criar_conta_pagar_tarifa_full_nf,
    _observacao_conta_tarifa_full_nf_com_canal,
    _resolver_classificacao_tarifa_full_nf,
)
from .estoque_saida_full.estoque import (
    _produto_usa_estoque_virtual_full_nf,
    _resolver_produto_full_nf,
    _sku_produto,
)
from .estoque_saida_full import estoque as _estoque_core
from .estoque_saida_full.nf_routes import (
    _buscar_baixas_full_nf,
    _canal_saida_full_por_observacao,
    _observacao_full_nf,
    _observacao_full_nf_com_canal_atualizado,
)
from .estoque_saida_full.parsers import (
    _char_sku_valido,
    _consumir_numero_quantidade,
    _extrair_itens_full_pdf,
    _extrair_quantidade_explicita,
    _extrair_sku_explicito,
    _extrair_sku_quantidade_linha,
    _parse_saida_full_xml,
    _posicao_valor_apos_rotulo,
    _texto_busca_sem_acento,
    _to_float_br,
    _xml_find_text,
)
from .estoque_saida_full.routes import router
from .estoque_saida_full.schemas import (
    SaidaFullNFCanalUpdateRequest,
    SaidaFullNFItemRequest,
    SaidaFullNFRequest,
)
from .services.kit_estoque_service import KitEstoqueService

__all__ = [
    "router",
    "SaidaFullNFCanalUpdateRequest",
    "SaidaFullNFItemRequest",
    "SaidaFullNFRequest",
    "_CANAL_LABELS",
    "_texto_limpo",
    "_resolver_produto_full_nf",
    "_observacao_full_nf",
    "_observacao_full_nf_com_canal_atualizado",
    "_canal_saida_full_por_observacao",
    "_sku_produto",
    "_produto_usa_estoque_virtual_full_nf",
    "_estoque_disponivel_saida_full_nf",
    "_processar_item_saida_full_nf",
    "_processar_item_kit_virtual_saida_full_nf",
    "_problemas_estoque_saida_full_nf",
    "_validar_estoque_saida_full_nf",
    "_buscar_baixas_full_nf",
    "_resolver_classificacao_tarifa_full_nf",
    "_criar_conta_pagar_tarifa_full_nf",
    "_observacao_conta_tarifa_full_nf_com_canal",
    "_buscar_conta_tarifa_full_nf",
    "_extrair_itens_full_pdf",
    "_parse_saida_full_xml",
    "_texto_busca_sem_acento",
    "_char_sku_valido",
    "_posicao_valor_apos_rotulo",
    "_extrair_sku_explicito",
    "_consumir_numero_quantidade",
    "_extrair_quantidade_explicita",
    "_extrair_sku_quantidade_linha",
    "_to_float_br",
    "_xml_find_text",
]


def _sincronizar_compatibilidade_kit_service() -> None:
    _estoque_core.KitEstoqueService = KitEstoqueService


def _estoque_disponivel_saida_full_nf(db, tenant_id: int, produto):
    _sincronizar_compatibilidade_kit_service()
    return _estoque_core._estoque_disponivel_saida_full_nf(db, tenant_id, produto)


def _processar_item_kit_virtual_saida_full_nf(
    db,
    tenant_id: int,
    produto,
    item,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user,
    permitir_estoque_negativo: bool = False,
):
    _sincronizar_compatibilidade_kit_service()
    return _estoque_core._processar_item_kit_virtual_saida_full_nf(
        db,
        tenant_id,
        produto,
        item,
        numero_nf,
        observacao_movimentacao,
        current_user,
        permitir_estoque_negativo,
    )


def _processar_item_saida_full_nf(
    db,
    tenant_id: int,
    item,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user,
    permitir_estoque_negativo: bool = False,
):
    _sincronizar_compatibilidade_kit_service()
    return _estoque_core._processar_item_saida_full_nf(
        db,
        tenant_id,
        item,
        numero_nf,
        observacao_movimentacao,
        current_user,
        permitir_estoque_negativo,
    )


def _problemas_estoque_saida_full_nf(db, tenant_id: int, itens):
    _sincronizar_compatibilidade_kit_service()
    return _estoque_core._problemas_estoque_saida_full_nf(db, tenant_id, itens)


def _validar_estoque_saida_full_nf(db, tenant_id: int, itens) -> None:
    _sincronizar_compatibilidade_kit_service()
    return _estoque_core._validar_estoque_saida_full_nf(db, tenant_id, itens)
