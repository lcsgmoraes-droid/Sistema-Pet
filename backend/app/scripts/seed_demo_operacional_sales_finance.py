"""Receivable and commission helpers for the operational demo seed."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_data import (
    DEFAULT_COMMISSION_PERCENT,
    DEFAULT_TAX_PERCENT,
    SaleScenario,
    money,
)
from app.scripts.seed_demo_operacional_db import _all_mappings, _scalar
from app.scripts.seed_demo_operacional_movements import _insert_payable_with_payment
from app.scripts.seed_demo_operacional_payments import _PAYMENT_PROFILES


def _insert_sale_item(
    db,
    *,
    tenant_id: str,
    sale_id: int,
    item: dict[str, Any],
    sale_number: str,
    user_id: int,
    sale_dt: datetime,
) -> None:
    product = item["product"]
    qty = item["qty"]
    unit_price = item["unit_price"]
    subtotal = item["subtotal"]
    db.execute(
        text(
            """
            INSERT INTO venda_itens (
                venda_id, tipo, produto_id, quantidade, preco_unitario,
                desconto_item, subtotal, created_at, tenant_id
            )
            VALUES (
                :sale_id, 'produto', :product_id, :qty, :unit_price,
                0, :subtotal, :created_at, :tenant_id
            )
            """
        ),
        {
            "sale_id": sale_id,
            "product_id": product["id"],
            "qty": qty,
            "unit_price": unit_price,
            "subtotal": subtotal,
            "created_at": sale_dt,
            "tenant_id": tenant_id,
        },
    )
    old_qty = money(product["baseline"] - product["sold_qty"])
    new_qty = money(old_qty - qty)
    product["sold_qty"] = money(product["sold_qty"] + qty)
    db.execute(
        text(
            """
            INSERT INTO estoque_movimentacoes (
                produto_id, tipo, motivo, quantidade, quantidade_anterior,
                quantidade_nova, custo_unitario, valor_total, estoque_origem,
                documento, referencia_id, referencia_tipo, observacao, user_id,
                created_at, updated_at, tenant_id, status
            )
            VALUES (
                :product_id, 'saida', 'venda', :qty, :old_qty,
                :new_qty, :cost, :total_cost, 'fisico',
                :document, :sale_id, 'venda',
                'Demo operacional - baixa de estoque por venda', :user_id,
                :created_at, :created_at, :tenant_id, 'confirmado'
            )
            """
        ),
        {
            "product_id": product["id"],
            "qty": qty,
            "old_qty": old_qty,
            "new_qty": new_qty,
            "cost": product["preco_custo"],
            "total_cost": money(product["preco_custo"] * qty),
            "document": sale_number,
            "sale_id": sale_id,
            "user_id": user_id,
            "created_at": sale_dt,
            "tenant_id": tenant_id,
        },
    )


def _insert_receivable(
    db,
    *,
    tenant_id: str,
    user_id: int,
    sale_id: int,
    client_id: int,
    category_id: int,
    dre_subcategory_id: int,
    payment_id: int,
    scenario: SaleScenario,
    total: Decimal,
    discount: Decimal,
    received_amount: Decimal,
    sale_day: date,
    due_date: date,
    received_date: date | None,
    status: str,
    card_fee: Decimal,
) -> int:
    liquid_estimated = money(total - card_fee)
    return int(
        _scalar(
            db,
            """
            INSERT INTO contas_receber (
                descricao, cliente_id, categoria_id, forma_pagamento_id,
                dre_subcategoria_id, canal, valor_original, valor_recebido,
                valor_desconto, valor_juros, valor_multa, valor_final,
                data_emissao, data_vencimento, data_recebimento, status,
                eh_parcelado, numero_parcela, total_parcelas, venda_id,
                documento, observacoes, beneficiario, tipo_documento,
                nsu, adquirente, conciliado, data_conciliacao,
                status_conciliacao, taxa_mdr_estimada, taxa_mdr_real,
                valor_liquido_estimado, valor_liquido_real,
                data_vencimento_estimada, data_vencimento_real,
                tipo_recebimento, data_liquidacao, user_id, created_at,
                updated_at, tenant_id
            )
            VALUES (
                :description, :client_id, :category_id, :payment_id,
                :dre_subcategory_id, :channel, :total, :received,
                :discount, 0, 0, :total,
                :sale_day, :due_date, :received_date, :status,
                :parcelado, 1, :installments, :sale_id,
                :document, :observations, :beneficiario, 'venda',
                :nsu, :adquirente, :conciliado, :data_conciliacao,
                :status_conciliacao, :taxa_mdr, :taxa_mdr,
                :liquid_estimated, :liquid_real,
                :due_date, :due_date,
                :tipo_recebimento, :data_liquidacao, :user_id, now(),
                now(), :tenant_id
            )
            RETURNING id
            """,
            {
                "description": f"Demo operacional - Receber {scenario.number}",
                "client_id": client_id,
                "category_id": category_id,
                "payment_id": payment_id,
                "dre_subcategory_id": dre_subcategory_id,
                "channel": scenario.channel,
                "total": total,
                "received": received_amount,
                "discount": discount,
                "sale_day": sale_day,
                "due_date": due_date,
                "received_date": received_date
                if scenario.received_ratio >= 1
                else None,
                "status": status,
                "parcelado": scenario.installments > 1,
                "installments": scenario.installments,
                "sale_id": sale_id,
                "document": f"DEMO-CR-{scenario.number[-3:]}",
                "observations": f"Demo operacional - previsao/baixa {scenario.number}",
                "beneficiario": f"Cliente demo {scenario.client_key}",
                "nsu": f"DEMO-NSU-{scenario.number[-3:]}"
                if scenario.payment_key in {"debito", "credito"}
                else None,
                "adquirente": "Stone"
                if scenario.payment_key in {"debito", "credito"}
                else None,
                "conciliado": scenario.received_ratio >= 1,
                "data_conciliacao": received_date
                if scenario.received_ratio >= 1
                else None,
                "status_conciliacao": "liquidada"
                if scenario.received_ratio >= 1
                else "confirmada_operadora"
                if scenario.received_ratio > 0
                else "prevista",
                "taxa_mdr": Decimal("3.49")
                if scenario.payment_key == "credito"
                else Decimal("1.89")
                if scenario.payment_key == "debito"
                else None,
                "liquid_estimated": liquid_estimated,
                "liquid_real": liquid_estimated
                if scenario.received_ratio >= 1
                else None,
                "tipo_recebimento": "parcela_individual"
                if scenario.installments > 1
                else "avista",
                "data_liquidacao": received_date
                if scenario.received_ratio >= 1
                else None,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _insert_commissions_for_sale(
    db,
    *,
    tenant_id: str,
    user_id: int,
    sale_id: int,
    scenario: SaleScenario,
    support: dict[str, Any],
    total: Decimal,
    subtotal: Decimal,
    discount: Decimal,
    card_fee: Decimal,
    sale_day: date,
    sale_dt: datetime,
) -> None:
    funcionario_id = support["people"]["funcionario_vendedor"]
    tax_amount = money((total * DEFAULT_TAX_PERCENT) / Decimal("100"))
    delivery_cost = scenario.driver_share
    sale_items = _all_mappings(
        db,
        """
        SELECT vi.id,
               vi.produto_id,
               vi.quantidade,
               vi.subtotal,
               p.preco_custo,
               p.categoria_id,
               p.subcategoria
        FROM venda_itens vi
        LEFT JOIN produtos p ON p.id = vi.produto_id
        WHERE vi.tenant_id = :tenant_id
          AND vi.venda_id = :sale_id
        ORDER BY vi.id
        """,
        {"tenant_id": tenant_id, "sale_id": sale_id},
    )
    if not sale_items:
        return

    commission_total = Decimal("0.00")
    item_rows: list[int] = []
    paid_ratio = min(max(scenario.received_ratio, Decimal("0")), Decimal("1"))

    for sale_item in sale_items:
        item_subtotal = money(sale_item["subtotal"] or 0)
        ratio = (item_subtotal / subtotal) if subtotal > 0 else Decimal("0")
        item_discount = money(discount * ratio)
        item_card_fee = money(card_fee * ratio)
        item_tax = money(tax_amount * ratio)
        item_delivery = money(delivery_cost * ratio)
        full_base = money(
            max(
                item_subtotal
                - item_discount
                - item_card_fee
                - item_tax
                - item_delivery,
                Decimal("0"),
            )
        )
        full_commission = money(full_base * DEFAULT_COMMISSION_PERCENT / Decimal("100"))
        generated_commission = money(full_commission * paid_ratio)
        if generated_commission <= 0:
            continue

        row_id = int(
            _scalar(
                db,
                """
                INSERT INTO comissoes_itens (
                    venda_id, venda_item_id, funcionario_id, produto_id,
                    categoria_id, subcategoria_id, tenant_id, data_venda,
                    quantidade, valor_venda, valor_custo, tipo_calculo,
                    valor_base_calculo, percentual_comissao, valor_comissao,
                    valor_comissao_gerada, valor_base_original,
                    valor_base_comissionada, percentual_aplicado,
                    taxa_cartao_item, impostos_item, taxa_entregador_item,
                    custo_operacional_item, receita_taxa_entrega_item,
                    percentual_impostos, percentual_pago, valor_pago_referencia,
                    parcela_numero, data_pagamento, forma_pagamento, valor_pago,
                    saldo_restante, observacao_pagamento, status,
                    data_criacao, data_atualizacao, comissao_provisionada
                )
                VALUES (
                    :sale_id, :sale_item_id, :funcionario_id, :product_id,
                    :category_id, NULL, :tenant_id, :sale_day,
                    :qty, :item_subtotal, :item_cost, 'percentual_venda_liquida',
                    :base, :percent, :commission,
                    :commission, :item_subtotal,
                    :base, :percent,
                    :card_fee, :tax, :delivery,
                    0, :delivery_revenue,
                    :tax_percent, :paid_percent, :paid_ref,
                    1, :payment_date, :payment_label, :paid_ref,
                    :saldo_restante, :obs, 'pendente',
                    :created_at, :created_at, false
                )
                RETURNING id
                """,
                {
                    "sale_id": sale_id,
                    "sale_item_id": sale_item["id"],
                    "funcionario_id": funcionario_id,
                    "product_id": sale_item["produto_id"],
                    "category_id": sale_item["categoria_id"],
                    "tenant_id": tenant_id,
                    "sale_day": sale_day,
                    "qty": sale_item["quantidade"],
                    "item_subtotal": item_subtotal,
                    "item_cost": money(
                        Decimal(str(sale_item["preco_custo"] or 0))
                        * Decimal(str(sale_item["quantidade"] or 0))
                    ),
                    "base": full_base,
                    "percent": DEFAULT_COMMISSION_PERCENT,
                    "commission": generated_commission,
                    "card_fee": item_card_fee,
                    "tax": item_tax,
                    "delivery": item_delivery,
                    "delivery_revenue": money(scenario.delivery_fee * ratio),
                    "tax_percent": DEFAULT_TAX_PERCENT,
                    "paid_percent": money(paid_ratio * Decimal("100")),
                    "paid_ref": money(total * paid_ratio),
                    "payment_date": sale_day if paid_ratio > 0 else None,
                    "payment_label": _PAYMENT_PROFILES[scenario.payment_key]["label"],
                    "saldo_restante": money(full_commission - generated_commission),
                    "obs": f"Demo operacional - comissão {scenario.number}",
                    "created_at": sale_dt,
                },
            )
        )
        item_rows.append(row_id)
        commission_total = money(commission_total + generated_commission)

    if commission_total <= 0:
        return

    payable_id = _insert_payable_with_payment(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        supplier_id=funcionario_id,
        category=support["categories"]["comissoes_vendas"],
        payment_id=support["payments"]["pix"],
        bank_id=support["banks"]["main"],
        document=f"DEMO-CP-COM-{scenario.number[-3:]}",
        description=f"Demo operacional - Comissao venda {scenario.number}",
        amount=commission_total,
        issue_date=sale_day,
        due_date=sale_day + timedelta(days=7),
        paid=False,
        channel=scenario.channel,
    )

    db.execute(
        text(
            """
            UPDATE comissoes_itens
            SET comissao_provisionada = true,
                conta_pagar_id = :payable_id,
                data_provisao = :sale_day,
                data_atualizacao = now()
            WHERE tenant_id = :tenant_id
              AND id = ANY(:item_ids)
            """
        ),
        {
            "payable_id": payable_id,
            "sale_day": sale_day,
            "tenant_id": tenant_id,
            "item_ids": item_rows,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO comissoes_vendas (
                venda_id, funcionario_id, conta_pagar_id, user_id, tenant_id,
                valor_venda, valor_comissao, percentual, status,
                created_at, updated_at
            )
            VALUES (
                :sale_id, :funcionario_id, :payable_id, :user_id, :tenant_id,
                :total, :commission_total, :percent, 'pendente',
                now(), now()
            )
            """
        ),
        {
            "sale_id": sale_id,
            "funcionario_id": funcionario_id,
            "payable_id": payable_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "total": total,
            "commission_total": commission_total,
            "percent": DEFAULT_COMMISSION_PERCENT,
        },
    )


def _insert_receipt(
    db,
    *,
    tenant_id: str,
    user_id: int,
    receivable_id: int,
    payment_id: int,
    amount: Decimal,
    received_date: date,
    scenario: SaleScenario,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO recebimentos (
                conta_receber_id, forma_pagamento_id, valor_recebido,
                data_recebimento, observacoes, comprovante, user_id,
                created_at, tenant_id
            )
            VALUES (
                :receivable_id, :payment_id, :amount,
                :received_date, :obs, :comprovante, :user_id,
                now(), :tenant_id
            )
            """
        ),
        {
            "receivable_id": receivable_id,
            "payment_id": payment_id,
            "amount": amount,
            "received_date": received_date,
            "obs": f"Demo operacional - recebimento {scenario.number}",
            "comprovante": f"DEMO-COMP-REC-{scenario.number[-3:]}",
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_sale_baixa(
    db,
    *,
    tenant_id: str,
    user_id: int,
    sale_id: int,
    total: Decimal,
    received_amount: Decimal,
    payment_label: str,
    sale_dt: datetime,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO venda_baixas (
                venda_id, valor_baixa, valor_anterior, valor_restante,
                forma_pagamento, tipo, usuario_id, observacoes, data_baixa,
                editado, excluido, created_at, tenant_id
            )
            VALUES (
                :sale_id, :received_amount, :total, :restante,
                :payment_label, :tipo, :user_id,
                'Demo operacional - baixa de venda', :sale_dt,
                false, false, now(), :tenant_id
            )
            """
        ),
        {
            "sale_id": sale_id,
            "received_amount": received_amount,
            "total": total,
            "restante": money(total - received_amount),
            "payment_label": payment_label,
            "tipo": "baixa_total" if received_amount >= total else "baixa_parcial",
            "user_id": user_id,
            "sale_dt": sale_dt,
            "tenant_id": tenant_id,
        },
    )
