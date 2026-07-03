"""Financial, bank, cash and stock movements for the operational demo seed."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import text

from app.scripts.seed_demo_operacional_data import build_fixed_payables, money
from app.scripts.seed_demo_operacional_db import _scalar


def _insert_financial_movement(
    db,
    *,
    tenant_id: str,
    user_id: int,
    bank_id: int,
    category_id: int | None,
    payment_id: int | None,
    kind: str,
    amount: Decimal,
    document: str,
    description: str,
    origin_type: str,
    origin_id: int,
    movement_dt: datetime,
    origin_channel: str | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_financeiras (
                data_movimento, tipo, valor, conta_bancaria_id, categoria_id,
                forma_pagamento_id, origem_tipo, origem_id, origem_venda,
                status, documento, descricao, observacoes, user_id,
                created_at, updated_at, tenant_id
            )
            VALUES (
                :movement_dt, :kind, :amount, :bank_id, :category_id,
                :payment_id, :origin_type, :origin_id, :origin_channel,
                'realizado', :document, :description,
                'Demo operacional', :user_id, now(), now(), :tenant_id
            )
            """
        ),
        {
            "movement_dt": movement_dt,
            "kind": kind,
            "amount": amount,
            "bank_id": bank_id,
            "category_id": category_id,
            "payment_id": payment_id,
            "origin_type": origin_type,
            "origin_id": origin_id,
            "origin_channel": origin_channel,
            "document": document,
            "description": description,
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_bank_movement(
    db,
    *,
    tenant_id: str,
    user_id: int,
    bank_id: int,
    amount: Decimal,
    kind: str,
    document: str,
    memo: str,
    movement_dt: datetime,
    receivable_id: int | None = None,
    payable_id: int | None = None,
    supplier_id: int | None = None,
    category_dre_id: int | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_bancarias (
                conta_bancaria_id, fitid, data_movimento, valor, tipo,
                memo, status_conciliacao, confianca_sugestao, tipo_vinculo,
                fornecedor_id, conta_pagar_id, conta_receber_id,
                categoria_dre_id, classificado_por, classificado_em,
                criado_em, atualizado_em, tenant_id
            )
            VALUES (
                :bank_id, :document, :movement_dt, :signed_amount, :kind,
                :memo, 'conciliado', 98, :tipo_vinculo,
                :supplier_id, :payable_id, :receivable_id,
                :category_dre_id, :user_id, now(),
                now(), now(), :tenant_id
            )
            """
        ),
        {
            "bank_id": bank_id,
            "document": document,
            "movement_dt": movement_dt,
            "signed_amount": amount if kind == "entrada" else -amount,
            "kind": kind,
            "memo": memo,
            "tipo_vinculo": "conta_receber" if receivable_id else "conta_pagar",
            "supplier_id": supplier_id,
            "payable_id": payable_id,
            "receivable_id": receivable_id,
            "category_dre_id": category_dre_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_cash_movement(
    db,
    *,
    tenant_id: str,
    cashier_id: int,
    sale_id: int,
    user_id: int,
    user_name: str,
    amount: Decimal,
    payment_label: str,
    document: str,
    movement_dt: datetime,
    description: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_caixa (
                caixa_id, tipo, valor, forma_pagamento, descricao, categoria,
                documento, venda_id, usuario_id, usuario_nome, data_movimento,
                tenant_id, created_at, updated_at
            )
            VALUES (
                :cashier_id, 'entrada', :amount, :payment_label,
                :description, 'Venda', :document, :sale_id,
                :user_id, :user_name, :movement_dt, :tenant_id, now(), now()
            )
            """
        ),
        {
            "cashier_id": cashier_id,
            "amount": amount,
            "payment_label": payment_label,
            "description": description,
            "document": document,
            "sale_id": sale_id,
            "user_id": user_id,
            "user_name": user_name,
            "movement_dt": movement_dt,
            "tenant_id": tenant_id,
        },
    )


def _insert_legacy_cashflow(
    db,
    *,
    tenant_id: str,
    user_id: int,
    kind: str,
    category: str,
    description: str,
    amount: Decimal,
    movement_dt: datetime,
    status: str,
    origin_type: str,
    origin_id: int,
    predicted_dt: datetime | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO fluxo_caixa (
                usuario_id, tipo, categoria, descricao, valor,
                data_movimentacao, data_prevista, status, origem_tipo,
                origem_id, criado_em, atualizado_em, tenant_id
            )
            VALUES (
                :user_id, :kind, :category, :description, :amount,
                :movement_dt, :predicted_dt, :status, :origin_type,
                :origin_id, now(), now(), :tenant_id
            )
            """
        ),
        {
            "user_id": user_id,
            "kind": kind,
            "category": category,
            "description": description,
            "amount": amount,
            "movement_dt": movement_dt,
            "predicted_dt": predicted_dt,
            "status": status,
            "origin_type": origin_type,
            "origin_id": origin_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_payable_with_payment(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    category: dict[str, Any],
    payment_id: int,
    bank_id: int,
    document: str,
    description: str,
    amount: Decimal,
    issue_date: date,
    due_date: date,
    paid: bool,
    channel: str | None,
) -> int:
    payable_id = int(
        _scalar(
            db,
            """
            INSERT INTO contas_pagar (
                descricao, fornecedor_id, categoria_id, dre_subcategoria_id,
                canal, valor_original, valor_pago, valor_desconto, valor_juros,
                valor_multa, valor_final, data_emissao, data_vencimento,
                data_pagamento, status, eh_parcelado, eh_recorrente, documento,
                observacoes, beneficiario, tipo_documento, afeta_dre,
                percentual_online, percentual_loja, user_id, created_at,
                updated_at, tenant_id
            )
            VALUES (
                :description, :supplier_id, :category_id, :dre_subcategory_id,
                :channel, :amount, :paid_amount, 0, 0,
                0, :amount, :issue_date, :due_date,
                :payment_date, :status, false, false, :document,
                'Demo operacional', :beneficiario, 'demo',
                true, :online, :loja, :user_id, now(),
                now(), :tenant_id
            )
            RETURNING id
            """,
            {
                "description": description,
                "supplier_id": supplier_id,
                "category_id": category["category_id"],
                "dre_subcategory_id": category["dre_subcategory_id"],
                "channel": channel,
                "amount": amount,
                "paid_amount": amount if paid else Decimal("0"),
                "issue_date": issue_date,
                "due_date": due_date,
                "payment_date": due_date if paid else None,
                "status": "pago" if paid else "pendente",
                "document": document,
                "beneficiario": description.replace("Demo operacional - ", ""),
                "online": 100 if channel in {"app_mobile", "ecommerce"} else 0,
                "loja": 0 if channel in {"app_mobile", "ecommerce"} else 100,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )
    if paid:
        db.execute(
            text(
                """
                INSERT INTO pagamentos (
                    conta_pagar_id, forma_pagamento_id, valor_pago,
                    data_pagamento, observacoes, comprovante, user_id,
                    created_at, tenant_id
                )
                VALUES (
                    :payable_id, :payment_id, :amount,
                    :payment_date, :obs, :comprovante, :user_id,
                    now(), :tenant_id
                )
                """
            ),
            {
                "payable_id": payable_id,
                "payment_id": payment_id,
                "amount": amount,
                "payment_date": due_date,
                "obs": "Demo operacional - pagamento efetuado",
                "comprovante": f"DEMO-COMP-PAG-{document[-3:]}",
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
        movement_dt = datetime.combine(due_date, time(hour=16))
        _insert_financial_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            category_id=category["category_id"],
            payment_id=payment_id,
            kind="saida",
            amount=amount,
            document=document,
            description=description,
            origin_type="conta_pagar",
            origin_id=payable_id,
            movement_dt=movement_dt,
            origin_channel=channel,
        )
        _insert_bank_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            amount=amount,
            kind="saida",
            document=f"DEMO-BANK-{document[-3:]}",
            memo=description,
            movement_dt=movement_dt,
            payable_id=payable_id,
            supplier_id=supplier_id,
            category_dre_id=category["dre_subcategory_id"],
        )
        _insert_legacy_cashflow(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="despesa",
            category="Conta a pagar",
            description=description,
            amount=amount,
            movement_dt=movement_dt,
            status="realizado",
            origin_type="demo_operacional",
            origin_id=payable_id,
        )
    else:
        _insert_legacy_cashflow(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="despesa",
            category="Conta a pagar",
            description=description,
            amount=amount,
            movement_dt=datetime.combine(issue_date, time(hour=10)),
            predicted_dt=datetime.combine(due_date, time(hour=10)),
            status="previsto",
            origin_type="demo_operacional",
            origin_id=payable_id,
        )
    return payable_id


def _insert_fixed_payables(
    db,
    *,
    tenant_id: str,
    user_id: int,
    support: dict[str, Any],
    base_date: date,
) -> list[int]:
    result = []
    for payable in build_fixed_payables():
        issue = base_date - timedelta(days=payable.days_ago)
        due = issue + timedelta(days=payable.due_in_days)
        result.append(
            _insert_payable_with_payment(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                supplier_id=support["people"][payable.supplier_key],
                category=support["categories"][payable.category_key],
                payment_id=support["payments"]["pix"],
                bank_id=support["banks"]["main"],
                document=payable.document,
                description=payable.description,
                amount=money(payable.amount),
                issue_date=issue,
                due_date=due,
                paid=payable.paid,
                channel=payable.channel,
            )
        )
    return result


def _insert_stock_purchase_movements(
    db,
    *,
    tenant_id: str,
    user_id: int,
    products: Iterable[dict[str, Any]],
    base_date: date,
) -> None:
    movement_dt = datetime.combine(base_date - timedelta(days=12), time(hour=9))
    for idx, product in enumerate(list(products)[:6]):
        qty = Decimal("10") + Decimal(idx * 2)
        old_qty = money(product["baseline"])
        new_qty = money(old_qty + qty)
        product["baseline"] = new_qty
        db.execute(
            text(
                """
                INSERT INTO estoque_movimentacoes (
                    produto_id, tipo, motivo, quantidade, quantidade_anterior,
                    quantidade_nova, custo_unitario, valor_total,
                    estoque_destino, documento, referencia_tipo, observacao,
                    user_id, created_at, updated_at, tenant_id, status
                )
                VALUES (
                    :product_id, 'entrada', 'compra', :qty, :old_qty,
                    :new_qty, :cost, :total_cost,
                    'fisico', 'DEMO-COMPRA-ESTOQUE', 'compra',
                    'Demo operacional - entrada por compra',
                    :user_id, :created_at, :created_at, :tenant_id, 'confirmado'
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
                "user_id": user_id,
                "created_at": movement_dt,
                "tenant_id": tenant_id,
            },
        )


def _finalize_product_stock(
    db, *, tenant_id: str, products: Iterable[dict[str, Any]]
) -> None:
    for product in products:
        final_qty = money(product["baseline"] - product["sold_qty"])
        db.execute(
            text(
                """
                UPDATE produtos
                SET estoque_atual = :final_qty,
                    estoque_fisico = GREATEST(:final_qty - 8, 0),
                    estoque_ecommerce = LEAST(:final_qty, 8),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :product_id
                """
            ),
            {
                "final_qty": final_qty,
                "tenant_id": tenant_id,
                "product_id": product["id"],
            },
        )
