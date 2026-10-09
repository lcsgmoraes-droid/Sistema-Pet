"""Escopo do recebimento, independente do caixa de origem da venda."""

from sqlalchemy import and_, func

from app.vendas_models import VendaPagamento


def filtro_pagamentos_caixa(caixa):
    # Nunca inferir pelo caixa original da venda: após a reabertura esse intervalo
    # muda. Legados só entram quando a migração conseguiu atribuí-los com segurança.
    return and_(
        VendaPagamento.caixa_id == caixa.id,
        func.coalesce(VendaPagamento.status, "").notin_(
            ["estornado", "recusado", "cancelado"]
        ),
    )
