# -*- coding: utf-8 -*-
"""Fachada compativel do orquestrador central de vendas.

O comportamento critico fica em modulos especializados para manter os fluxos de
PDV, financeiro e estoque compreensiveis sem alterar a API publica de
``VendaService``.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.vendas.cancelamento_service import cancelar_venda as cancelar_venda_impl
from app.vendas.criacao import criar_venda as criar_venda_impl
from app.vendas.estoque_baixa import (
    processar_baixa_estoque_item as processar_baixa_estoque_item_impl,
)
from app.vendas.finalizacao import (
    _calcular_pagamentos_finalizacao,
    finalizar_venda as finalizar_venda_impl,
)
from app.vendas.numeracao import gerar_numero_venda as gerar_numero_venda_impl
from app.vendas.pos_processamento import (
    gerar_dre_competencia_venda,
    processar_comissoes_venda,
    processar_contas_pagar_entrega,
    processar_contas_pagar_taxas,
    processar_lembretes_venda,
)

__all__ = [
    "VendaService",
    "_calcular_pagamentos_finalizacao",
    "gerar_dre_competencia_venda",
    "processar_comissoes_venda",
    "processar_contas_pagar_entrega",
    "processar_contas_pagar_taxas",
    "processar_lembretes_venda",
]


class VendaService:
    """Servico orquestrador para vendas com transacao atomica."""

    _gerar_numero_venda = staticmethod(gerar_numero_venda_impl)
    _processar_baixa_estoque_item = staticmethod(processar_baixa_estoque_item_impl)
    cancelar_venda = staticmethod(cancelar_venda_impl)

    @staticmethod
    def criar_venda(
        payload: Dict[str, Any], user_id: int, db: Session
    ) -> Dict[str, Any]:
        return criar_venda_impl(
            payload=payload,
            user_id=user_id,
            db=db,
            gerar_numero_venda=VendaService._gerar_numero_venda,
            processar_baixa_estoque_item=VendaService._processar_baixa_estoque_item,
        )

    @staticmethod
    def finalizar_venda(
        venda_id: int,
        pagamentos: List[Dict[str, Any]],
        user_id: int,
        user_nome: str,
        tenant_id: str,
        db: Session,
        cupom_code: Optional[str] = None,
        cupom_discount_applied: Optional[float] = None,
        caixa_id: Optional[int] = None,
        permitir_caixa_tenant: bool = False,
    ) -> Dict[str, Any]:
        return finalizar_venda_impl(
            venda_id=venda_id,
            pagamentos=pagamentos,
            user_id=user_id,
            user_nome=user_nome,
            tenant_id=tenant_id,
            db=db,
            cupom_code=cupom_code,
            cupom_discount_applied=cupom_discount_applied,
            caixa_id=caixa_id,
            permitir_caixa_tenant=permitir_caixa_tenant,
            processar_baixa_estoque_item=VendaService._processar_baixa_estoque_item,
        )
