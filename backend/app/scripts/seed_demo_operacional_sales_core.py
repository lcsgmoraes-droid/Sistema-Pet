"""Sale orchestration helpers for the operational demo seed."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_data import SaleScenario, decimal_json, money
from app.scripts.seed_demo_operacional_db import _one_mapping, _scalar
from app.scripts.seed_demo_operacional_logistics import _insert_order, _insert_route
from app.scripts.seed_demo_operacional_movements import (
    _insert_bank_movement,
    _insert_cash_movement,
    _insert_financial_movement,
    _insert_legacy_cashflow,
    _insert_payable_with_payment,
)
from app.scripts.seed_demo_operacional_payments import _PAYMENT_PROFILES
from app.scripts.seed_demo_operacional_sales_finance import (
    _insert_commissions_for_sale,
    _insert_receipt,
    _insert_receivable,
    _insert_sale_baixa,
    _insert_sale_item,
)


def _discount_for(scenario: SaleScenario, subtotal: Decimal) -> Decimal:
    if scenario.discount_percent:
        return money(subtotal * scenario.discount_percent / Decimal("100"))
    return money(scenario.discount_value)


def _payment_profile(support: dict[str, Any], key: str) -> dict[str, Any]:
    payment_id = support["payments"][key]
    return _PAYMENT_PROFILES[key] | {"id": payment_id}


def _insert_cashier(
    db,
    *,
    tenant_id: str,
    user_id: int,
    user_name: str,
    bank_cash_id: int,
    base_date: date,
) -> int:
    opened_at = datetime.combine(
        base_date - timedelta(days=10), time(hour=8, minute=30)
    )
    return int(
        _scalar(
            db,
            """
            INSERT INTO caixas (
                numero_caixa, usuario_id, usuario_nome, data_abertura,
                data_fechamento, valor_abertura, valor_esperado, valor_informado,
                diferenca, status, conta_origem_id, conta_origem_nome,
                observacoes_abertura, observacoes_fechamento, tenant_id,
                created_at, updated_at
            )
            VALUES (
                9901, :user_id, :user_name, :opened_at,
                NULL, 600.00, NULL, NULL,
                NULL, 'aberto', :bank_cash_id, 'Caixa Loja Demo',
                'Demo operacional - caixa para videos', NULL, :tenant_id,
                now(), now()
            )
            RETURNING id
            """,
            {
                "user_id": user_id,
                "user_name": user_name,
                "opened_at": opened_at,
                "bank_cash_id": bank_cash_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _insert_sale(
    db,
    *,
    tenant_id: str,
    user_id: int,
    user_name: str,
    scenario: SaleScenario,
    items: list[dict[str, Any]],
    support: dict[str, Any],
    base_date: date,
    cashier_id: int,
) -> dict[str, Any]:
    sale_day = base_date - timedelta(days=scenario.days_ago)
    sale_dt = datetime.combine(
        sale_day, time(hour=10 + scenario.days_ago % 6, minute=15)
    )
    subtotal = money(sum(item["subtotal"] for item in items))
    discount = _discount_for(scenario, subtotal)
    total = money(subtotal - discount + scenario.delivery_fee)
    cmv = money(sum(item["product"]["preco_custo"] * item["qty"] for item in items))
    received_amount = money(total * scenario.received_ratio)
    payment = _payment_profile(support, scenario.payment_key)
    card_fee = money(
        total * payment["fee_percent"] / Decimal("100") + payment["fee_fixed"]
    )
    due_days = scenario.due_in_days or payment["due_days"]
    due_date = sale_day + timedelta(days=due_days)
    received_date = sale_day if scenario.received_ratio > 0 else None
    status_receivable = (
        "recebido"
        if scenario.received_ratio >= 1
        else "parcial"
        if scenario.received_ratio > 0
        else "pendente"
    )
    sale_status = "finalizada" if scenario.received_ratio >= 1 else "aberta"
    payment_record_value = total if scenario.received_ratio >= 1 else received_amount
    channel_category_key = (
        "receita_app"
        if scenario.channel == "app_mobile"
        else "receita_ecommerce"
        if scenario.channel == "ecommerce"
        else "receita_produtos"
    )
    receivable_category = support["categories"][channel_category_key]
    bank_id = support["banks"][payment["bank"]]
    client_id = support["people"][scenario.client_key]
    driver_id = support["people"]["entregador"] if scenario.delivery else None
    delivery_loja = money(scenario.delivery_fee - scenario.driver_share)
    snapshot = {
        "demo_operacional": True,
        "cmv_total": cmv,
        "taxa_cartao": card_fee,
        "taxa_entrega": scenario.delivery_fee,
        "repasse_entregador": scenario.driver_share,
        "cupom": scenario.coupon,
        "canal": scenario.channel,
    }

    sale_id = int(
        _scalar(
            db,
            """
            INSERT INTO vendas (
                numero_venda, cliente_id, vendedor_id, funcionario_id,
                subtotal, desconto_valor, desconto_percentual, cupom_code,
                cupom_discount_applied, total, tem_entrega, taxa_entrega,
                percentual_taxa_entregador, percentual_taxa_loja,
                valor_taxa_entregador, valor_taxa_loja, entregador_id,
                loja_origem, endereco_entrega, distancia_km, valor_por_km,
                observacoes_entrega, status_entrega, data_entrega,
                ordem_entrega_otimizada, observacoes, caixa_id, canal,
                conciliado_vendas, conciliado_vendas_em, status, data_venda,
                data_finalizacao, dre_gerada, data_geracao_dre,
                rentabilidade_snapshot, rentabilidade_snapshot_em,
                tipo_retirada, palavra_chave_retirada, retirado_por,
                user_id, tenant_id, created_at, updated_at
            )
            VALUES (
                :number, :client_id, :user_id, :funcionario_id,
                :subtotal, :discount, :discount_percent, :coupon,
                :coupon_discount, :total, :delivery, :delivery_fee,
                :driver_percent, :store_percent,
                :driver_share, :delivery_loja, :driver_id,
                'Loja CorePet Demo', :delivery_address, :delivery_km, 2.20,
                :delivery_obs, :delivery_status, :delivery_date,
                NULL, :observations, :cashier_id, :channel,
                :conciliado, :conciliado_em, :sale_status, :sale_dt,
                :finalized_at, true, :sale_dt,
                CAST(:snapshot AS JSON), :sale_dt,
                :tipo_retirada, :palavra_chave, :retirado_por,
                :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "number": scenario.number,
                "client_id": client_id,
                "user_id": user_id,
                "funcionario_id": support["people"]["funcionario_vendedor"],
                "subtotal": subtotal,
                "discount": discount,
                "discount_percent": scenario.discount_percent,
                "coupon": scenario.coupon,
                "coupon_discount": discount if scenario.coupon else None,
                "total": total,
                "delivery": scenario.delivery,
                "delivery_fee": scenario.delivery_fee,
                "driver_percent": money(
                    (scenario.driver_share / scenario.delivery_fee * Decimal("100"))
                    if scenario.delivery_fee
                    else Decimal("0")
                ),
                "store_percent": money(
                    (delivery_loja / scenario.delivery_fee * Decimal("100"))
                    if scenario.delivery_fee
                    else Decimal("100")
                ),
                "driver_share": scenario.driver_share,
                "delivery_loja": delivery_loja,
                "driver_id": driver_id,
                "delivery_address": _delivery_address(db, client_id),
                "delivery_km": scenario.delivery_km or None,
                "delivery_obs": "Demo operacional - entrega com rota"
                if scenario.delivery
                else None,
                "delivery_status": _sale_delivery_status(scenario.route_status),
                "delivery_date": sale_dt + timedelta(hours=2)
                if scenario.route_status == "concluida"
                else None,
                "observations": f"Demo operacional - {scenario.observations}",
                "cashier_id": cashier_id,
                "channel": scenario.channel,
                "conciliado": scenario.received_ratio >= 1,
                "conciliado_em": sale_dt if scenario.received_ratio >= 1 else None,
                "sale_status": sale_status,
                "finalized_at": sale_dt if scenario.received_ratio >= 1 else None,
                "sale_dt": sale_dt,
                "snapshot": json.dumps(snapshot, default=decimal_json),
                "tipo_retirada": "proprio"
                if scenario.order_id and not scenario.delivery
                else None,
                "palavra_chave": "core-demo"
                if scenario.order_id and not scenario.delivery
                else None,
                "retirado_por": "Cliente demo"
                if scenario.order_id and not scenario.delivery
                else None,
                "tenant_id": tenant_id,
            },
        )
    )

    for item in items:
        _insert_sale_item(
            db,
            tenant_id=tenant_id,
            sale_id=sale_id,
            item=item,
            sale_number=scenario.number,
            user_id=user_id,
            sale_dt=sale_dt,
        )

    db.execute(
        text(
            """
            INSERT INTO venda_pagamentos (
                venda_id, forma_pagamento, valor, bandeira, numero_parcelas,
                numero_transacao, numero_autorizacao, nsu_cartao,
                status_conciliacao, valor_recebido, troco, status,
                data_pagamento, created_at, tenant_id
            )
            VALUES (
                :sale_id, :payment_label, :payment_record_value, :brand, :installments,
                :transaction, :authorization, :nsu,
                :conciliation_status, :received_amount, 0, :payment_status,
                :payment_dt, now(), :tenant_id
            )
            """
        ),
        {
            "sale_id": sale_id,
            "payment_label": payment["label"],
            "total": total,
            "payment_record_value": payment_record_value,
            "brand": scenario.card_brand,
            "installments": scenario.installments,
            "transaction": f"DEMO-TX-{scenario.number[-3:]}",
            "authorization": f"DEMO-AUT-{scenario.number[-3:]}",
            "nsu": f"DEMO-NSU-{scenario.number[-3:]}"
            if payment["fee_percent"]
            else None,
            "conciliation_status": "conciliado"
            if scenario.received_ratio >= 1
            else "nao_conciliado",
            "received_amount": received_amount,
            "payment_status": "aprovado" if received_amount > 0 else "pendente",
            "payment_dt": sale_dt,
            "tenant_id": tenant_id,
        },
    )

    receivable_id = _insert_receivable(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        sale_id=sale_id,
        client_id=client_id,
        category_id=receivable_category["category_id"],
        dre_subcategory_id=receivable_category["dre_subcategory_id"],
        payment_id=payment["id"],
        scenario=scenario,
        total=total,
        discount=discount,
        received_amount=received_amount,
        sale_day=sale_day,
        due_date=due_date,
        received_date=received_date,
        status=status_receivable,
        card_fee=card_fee,
    )

    if scenario.commissioned:
        _insert_commissions_for_sale(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            sale_id=sale_id,
            scenario=scenario,
            support=support,
            total=total,
            subtotal=subtotal,
            discount=discount,
            card_fee=card_fee,
            sale_day=sale_day,
            sale_dt=sale_dt,
        )

    if received_amount > 0:
        _insert_receipt(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            receivable_id=receivable_id,
            payment_id=payment["id"],
            amount=received_amount,
            received_date=received_date or sale_day,
            scenario=scenario,
        )
        _insert_sale_baixa(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            sale_id=sale_id,
            total=total,
            received_amount=received_amount,
            payment_label=payment["label"],
            sale_dt=sale_dt,
        )
        _insert_financial_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            category_id=receivable_category["category_id"],
            payment_id=payment["id"],
            kind="entrada",
            amount=received_amount,
            document=scenario.number,
            description=f"Demo operacional - recebimento {scenario.number}",
            origin_type="conta_receber",
            origin_id=receivable_id,
            movement_dt=datetime.combine(received_date or sale_day, time(hour=15)),
            origin_channel=scenario.channel,
        )
        _insert_bank_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            amount=received_amount,
            kind="entrada",
            document=f"DEMO-BANK-{scenario.number[-3:]}",
            memo=f"Demo operacional recebimento {scenario.number}",
            movement_dt=datetime.combine(received_date or sale_day, time(hour=15)),
            receivable_id=receivable_id,
            category_dre_id=receivable_category["dre_subcategory_id"],
        )
        _insert_cash_movement(
            db,
            tenant_id=tenant_id,
            cashier_id=cashier_id,
            sale_id=sale_id,
            user_id=user_id,
            user_name=user_name,
            amount=received_amount,
            payment_label=payment["label"],
            document=scenario.number,
            movement_dt=sale_dt,
            description=f"Demo operacional - venda {scenario.number}",
        )
        _insert_legacy_cashflow(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="receita",
            category="Venda",
            description=f"Demo operacional - recebido {scenario.number}",
            amount=received_amount,
            movement_dt=datetime.combine(received_date or sale_day, time(hour=15)),
            status="realizado",
            origin_type="demo_operacional",
            origin_id=sale_id,
        )

    if card_fee > 0:
        _insert_payable_with_payment(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=support["people"]["fornecedor"],
            category=support["categories"]["taxas_cartao"],
            payment_id=support["payments"]["pix"],
            bank_id=support["banks"]["main"],
            document=f"DEMO-CP-TAXA-{scenario.number[-3:]}",
            description=f"Demo operacional - Taxa de cartao {scenario.number}",
            amount=card_fee,
            issue_date=sale_day,
            due_date=due_date,
            paid=scenario.received_ratio >= 1,
            channel=scenario.channel,
        )

    if scenario.delivery:
        _insert_route(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            scenario=scenario,
            sale_id=sale_id,
            driver_id=support["people"]["entregador"],
            sale_dt=sale_dt,
            address=_delivery_address(db, client_id),
        )
        _insert_payable_with_payment(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=support["people"]["entregador"],
            category=support["categories"]["repasse_entrega"],
            payment_id=support["payments"]["pix"],
            bank_id=support["banks"]["main"],
            document=f"DEMO-CP-ENT-{scenario.number[-3:]}",
            description=f"Demo operacional - Repasse entrega {scenario.number}",
            amount=scenario.driver_share,
            issue_date=sale_day,
            due_date=sale_day + timedelta(days=2),
            paid=scenario.route_status == "concluida",
            channel=scenario.channel,
        )

    if scenario.order_id:
        _insert_order(
            db,
            tenant_id=tenant_id,
            scenario=scenario,
            client_id=client_id,
            total=total,
            items=items,
        )

    return {
        "sale_id": sale_id,
        "number": scenario.number,
        "total": total,
        "received": received_amount,
        "cmv": cmv,
        "card_fee": card_fee,
        "delivery_driver": scenario.driver_share,
    }


def _delivery_address(db, client_id: int) -> str:
    row = _one_mapping(
        db,
        """
        SELECT COALESCE(
            endereco_entrega,
            endereco || ', ' || numero || ' - ' || bairro || ', ' || cidade || '/' || estado
        ) AS address
        FROM clientes WHERE id = :client_id
        """,
        {"client_id": client_id},
    )
    return row["address"] if row and row["address"] else "Endereco demo"


def _sale_delivery_status(route_status: str | None) -> str | None:
    if route_status == "concluida":
        return "entregue"
    if route_status == "em_rota":
        return "em_rota"
    if route_status == "pendente":
        return "pendente"
    return None
