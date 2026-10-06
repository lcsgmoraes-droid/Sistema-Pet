"""Pagamentos e custo de cashback após estorno de uma venda."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import insert

from app.campaigns.models import (
    CashbackSourceTypeEnum,
    CashbackTransaction,
)
from app.financeiro_models import LancamentoManual
from app.vendas.cashback_financeiro import (
    cancelar_despesas_cashback_venda,
    cashback_resgatado_liquido_por_transacao,
    cashback_resgatado_liquido_por_venda,
    remover_pagamentos_cashback_venda,
)
from app.vendas_models import Venda, VendaPagamento


def test_reopening_clears_only_its_cashback_payments_and_expenses(
    db_session, tenant_context
):
    tenant_id = uuid4()
    outro_tenant = uuid4()
    pagamentos = [
        VendaPagamento(
            tenant_id=tenant,
            venda_id=venda_id,
            forma_pagamento=forma,
            valor=Decimal("2.00"),
        )
        for tenant, venda_id, forma in (
            (tenant_id, 12, "Cashback"),
            (tenant_id, 12, "cashback"),
            (tenant_id, 12, "Cartão"),
            (tenant_id, 13, "Cashback"),
            (outro_tenant, 12, "Cashback"),
        )
    ]
    despesas = [
        LancamentoManual(
            tenant_id=tenant,
            user_id=1,
            tipo="saida",
            valor=Decimal("2.00"),
            descricao="Cashback resgatado",
            data_lancamento=date.today(),
            status="realizado",
            gerado_automaticamente=automatica,
            documento=documento,
        )
        for tenant, documento, automatica in (
            (tenant_id, "CASHBACK-VEN-12", True),
            (tenant_id, "CASHBACK-VEN-12", True),
            (tenant_id, "CASHBACK-VEN-12", False),
            (tenant_id, "CASHBACK-VEN-13", True),
            (outro_tenant, "CASHBACK-VEN-12", True),
        )
    ]
    tenant_context(tenant_id)
    db_session.add_all([*pagamentos[:4], *despesas[:4]])
    db_session.flush()
    tenant_context(outro_tenant)
    db_session.add_all([pagamentos[4], despesas[4]])
    db_session.flush()
    tenant_context(tenant_id)

    assert (
        remover_pagamentos_cashback_venda(db_session, tenant_id=tenant_id, venda_id=12)
        == 2
    )
    assert (
        cancelar_despesas_cashback_venda(
            db_session, tenant_id=tenant_id, numero_venda="VEN-12"
        )
        == 2
    )
    assert (
        cancelar_despesas_cashback_venda(
            db_session, tenant_id=tenant_id, numero_venda="VEN-12"
        )
        == 0
    )

    pagamentos_restantes = db_session.query(VendaPagamento).all()
    assert {
        (p.tenant_id, p.venda_id, p.forma_pagamento) for p in pagamentos_restantes
    } == {
        (tenant_id, 12, "Cartão"),
        (tenant_id, 13, "Cashback"),
    }
    tenant_context(outro_tenant)
    assert [
        (p.venda_id, p.forma_pagamento) for p in db_session.query(VendaPagamento)
    ] == [(12, "Cashback")]
    assert [despesa.status for despesa in despesas] == [
        "cancelado",
        "cancelado",
        "realizado",
        "realizado",
        "realizado",
    ]


def test_sale_reports_count_only_unreversed_redemptions(db_session, tenant_context):
    from app.dre_canais.agregacao import _bulk_cashback_por_venda
    from app.relatorio_vendas_preloads import _carregar_cashback_por_venda
    from app.services.venda_rentabilidade_snapshot_service import (
        _resolve_cashback_resgatado,
    )

    tenant_id = uuid4()
    outro_tenant = uuid4()
    rows = [
        (100, tenant_id, "redemption", 12, "-5.00", "debit"),
        (101, tenant_id, "reversal", 100, "3.00", "credit"),
        (102, tenant_id, "reversal", 100, "2.00", "credit"),
        (103, tenant_id, "redemption", 12, "-2.50", "debit"),
        (104, tenant_id, "redemption", 13, "-1.00", "debit"),
        (105, tenant_id, "redemption", 14, "-6.00", "debit"),
        (106, tenant_id, "reversal", 105, "0.00", "closed"),
        (107, outro_tenant, "redemption", 12, "-9.00", "debit"),
    ]
    tenant_context(tenant_id)
    db_session.execute(
        insert(CashbackTransaction),
        [
            {
                "id": row_id,
                "tenant_id": tenant,
                "customer_id": 42,
                "source_type": CashbackSourceTypeEnum(source_type),
                "source_id": source_id,
                "amount": Decimal(amount),
                "tx_type": tx_type,
                "created_at": datetime.now(timezone.utc),
            }
            for row_id, tenant, source_type, source_id, amount, tx_type in rows[:-1]
        ],
    )
    tenant_context(outro_tenant)
    row_id, tenant, source_type, source_id, amount, tx_type = rows[-1]
    db_session.execute(
        insert(CashbackTransaction),
        {
            "id": row_id,
            "tenant_id": tenant,
            "customer_id": 42,
            "source_type": CashbackSourceTypeEnum(source_type),
            "source_id": source_id,
            "amount": Decimal(amount),
            "tx_type": tx_type,
            "created_at": datetime.now(timezone.utc),
        },
    )
    tenant_context(tenant_id)

    assert cashback_resgatado_liquido_por_venda(
        db_session, tenant_id=tenant_id, venda_ids=[12, 13, 14]
    ) == {12: Decimal("2.50"), 13: Decimal("1.00"), 14: Decimal("0.00")}
    assert cashback_resgatado_liquido_por_transacao(
        db_session, tenant_id=tenant_id, redemption_ids=[100, 103, 105]
    ) == {100: Decimal("0.00"), 103: Decimal("2.50"), 105: Decimal("0.00")}
    assert _bulk_cashback_por_venda(db_session, tenant_id, [12, 13]) == {
        12: 2.5,
        13: 1.0,
    }
    assert _carregar_cashback_por_venda(db_session, tenant_id, [12, 13]) == {
        12: 2.5,
        13: 1.0,
    }
    assert _resolve_cashback_resgatado(db_session, tenant_id, 12) == 2.5
    assert _resolve_cashback_resgatado(db_session, tenant_id, 14) == 0.0


def test_reopen_removes_cashback_payment_before_refunding_wallet(
    db_session, tenant_context, monkeypatch
):
    from app.campaigns import cashback_sale_reversal, coupon_service, loyalty_service
    from app.services import business_audit_service
    from app.vendas import status_routes

    tenant_id = uuid4()
    tenant_context(tenant_id)
    venda = Venda(
        tenant_id=tenant_id,
        user_id=1,
        vendedor_id=1,
        cliente_id=42,
        numero_venda="VEN-REABERTA",
        subtotal=Decimal("10.00"),
        total=Decimal("10.00"),
        status="finalizada",
    )
    db_session.add(venda)
    db_session.flush()
    db_session.add_all(
        [
            VendaPagamento(
                tenant_id=tenant_id,
                venda_id=venda.id,
                forma_pagamento="Cashback",
                valor=Decimal("3.00"),
            ),
            VendaPagamento(
                tenant_id=tenant_id,
                venda_id=venda.id,
                forma_pagamento="Cartão",
                valor=Decimal("7.00"),
            ),
            LancamentoManual(
                tenant_id=tenant_id,
                user_id=1,
                tipo="saida",
                valor=Decimal("3.00"),
                descricao="Cashback resgatado",
                data_lancamento=date.today(),
                status="realizado",
                gerado_automaticamente=True,
                documento="CASHBACK-VEN-REABERTA",
            ),
        ]
    )
    db_session.flush()

    monkeypatch.setattr(
        Venda, "to_dict", lambda self: {"id": self.id, "status": self.status}
    )
    monkeypatch.setattr(
        coupon_service, "reverse_coupon_redemptions_for_sale", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        loyalty_service, "void_loyalty_stamps_for_sale", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        business_audit_service, "build_sale_reopened_metadata", lambda **k: {}
    )
    monkeypatch.setattr(business_audit_service, "log_business_event", lambda **k: None)
    monkeypatch.setattr(status_routes, "log_action", lambda **k: None)
    order = []
    monkeypatch.setattr(
        status_routes,
        "invalidate_venda_rentabilidade_snapshot",
        lambda *a: order.append("snapshot invalidado"),
    )

    def check_refund_order(*args, **kwargs):
        ativos = db_session.query(VendaPagamento).filter_by(venda_id=venda.id).all()
        assert [pag.forma_pagamento for pag in ativos] == ["Cartão"]
        order.append("cashback estornado")

    monkeypatch.setattr(
        cashback_sale_reversal, "reverse_cashback_for_sale", check_refund_order
    )
    result = status_routes.reabrir_venda(
        venda.id,
        db=db_session,
        user_and_tenant=(SimpleNamespace(id=1), tenant_id),
    )

    assert result == {"id": venda.id, "status": "aberta"}
    assert (
        db_session.query(LancamentoManual)
        .filter_by(documento="CASHBACK-VEN-REABERTA")
        .one()
        .status
        == "cancelado"
    )

    # A rota genérica de status também pode reabrir a venda.
    venda.status = "finalizada"
    db_session.add(
        VendaPagamento(
            tenant_id=tenant_id,
            venda_id=venda.id,
            forma_pagamento="Cashback",
            valor=Decimal("2.00"),
        )
    )
    db_session.add(
        LancamentoManual(
            tenant_id=tenant_id,
            user_id=1,
            tipo="saida",
            valor=Decimal("2.00"),
            descricao="Cashback resgatado novamente",
            data_lancamento=date.today(),
            status="realizado",
            gerado_automaticamente=True,
            documento="CASHBACK-VEN-REABERTA",
        )
    )
    db_session.flush()

    order.clear()
    result_patch = status_routes.atualizar_status_venda(
        venda.id,
        {"status": "aberta"},
        db=db_session,
        user_and_tenant=(SimpleNamespace(id=1), tenant_id),
    )
    assert result_patch == {"success": True, "status": "aberta"}
    assert order == ["cashback estornado", "snapshot invalidado"]
    assert [pag.forma_pagamento for pag in db_session.query(VendaPagamento)] == [
        "Cartão"
    ]
    assert all(
        lancamento.status == "cancelado"
        for lancamento in db_session.query(LancamentoManual)
    )

    # Um status antigo cancelado pode ainda ter parcela histórica de cashback.
    venda.status = "cancelada"
    db_session.add(
        VendaPagamento(
            tenant_id=tenant_id,
            venda_id=venda.id,
            forma_pagamento="Cashback",
            valor=Decimal("1.00"),
        )
    )
    db_session.flush()
    order.clear()
    status_routes.atualizar_status_venda(
        venda.id,
        {"status": "aberta"},
        db=db_session,
        user_and_tenant=(SimpleNamespace(id=1), tenant_id),
    )
    assert order == ["cashback estornado", "snapshot invalidado"]
    assert [pag.forma_pagamento for pag in db_session.query(VendaPagamento)] == [
        "Cartão"
    ]

    # Uma venda legada pode ter crédito de campanha pendente de estorno sem
    # parcela de cashback; o PATCH ainda executa a reversão idempotente.
    venda.status = "cancelada"
    order.clear()
    status_routes.atualizar_status_venda(
        venda.id,
        {"status": "aberta"},
        db=db_session,
        user_and_tenant=(SimpleNamespace(id=1), tenant_id),
    )
    assert order == ["cashback estornado", "snapshot invalidado"]

    venda.status = "cancelada"
    with pytest.raises(HTTPException) as exc_info:
        status_routes.atualizar_status_venda(
            venda.id,
            {"status": "finalizada"},
            db=db_session,
            user_and_tenant=(SimpleNamespace(id=1), tenant_id),
        )
    assert exc_info.value.status_code == 400
