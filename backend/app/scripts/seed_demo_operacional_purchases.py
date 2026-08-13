"""Purchase, invoice-confrontation and supplier-pending demo scenarios."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_db import _one_mapping, _scalar
from app.scripts.seed_demo_operacional_purchase_data import (
    DEMO_SUPPLIER_CNPJ,
    build_demo_purchase_scenarios,
    demo_xml as _demo_xml,
    invoice_key as _invoice_key,
    tenant_suffix as _tenant_suffix,
)


def _purchase_product(db, *, tenant_id: str) -> dict[str, Any]:
    product = _one_mapping(
        db,
        """
        SELECT id, codigo, nome,
               COALESCE(NULLIF(preco_custo, 0), 30.94) AS preco_custo,
               COALESCE(NULLIF(codigo_barras, ''), NULLIF(gtin_ean, ''), 'SEM GTIN') AS ean
        FROM produtos
        WHERE tenant_id = :tenant_id
          AND COALESCE(ativo, true) = true
          AND deleted_at IS NULL
          AND COALESCE(tipo_produto, 'SIMPLES') <> 'PAI'
        ORDER BY CASE WHEN codigo = '6083' OR codigo_barras = '7898242030076' THEN 0 ELSE 1 END,
                 nome, id
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if not product:
        raise ValueError(
            "O tenant Demo precisa ter ao menos um produto para os cenarios de compra."
        )
    return product


def _ensure_product_supplier(
    db, *, tenant_id: str, product: dict[str, Any], supplier_id: int
) -> str:
    existing = _one_mapping(
        db,
        """
        SELECT id, codigo_fornecedor FROM produto_fornecedores
        WHERE tenant_id = :tenant_id AND produto_id = :product_id
          AND fornecedor_id = :supplier_id
        ORDER BY e_principal DESC, id
        LIMIT 1
        """,
        {
            "tenant_id": tenant_id,
            "product_id": product["id"],
            "supplier_id": supplier_id,
        },
    )
    supplier_code = str(
        (existing or {}).get("codigo_fornecedor")
        or f"DEMO-{str(product.get('codigo') or product['id'])[:32]}"
    )
    payload = {
        "tenant_id": tenant_id,
        "product_id": product["id"],
        "supplier_id": supplier_id,
        "supplier_code": supplier_code,
        "cost": Decimal("30.94"),
    }
    db.execute(
        text(
            """
            UPDATE produto_fornecedores
            SET e_principal = false, updated_at = now()
            WHERE tenant_id = :tenant_id AND produto_id = :product_id
              AND fornecedor_id <> :supplier_id AND e_principal = true
            """
        ),
        payload,
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE produto_fornecedores
                SET codigo_fornecedor = :supplier_code, preco_custo = :cost,
                    prazo_entrega = 3, estoque_fornecedor = 250,
                    e_principal = true, ativo = true, updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing["id"]},
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO produto_fornecedores (
                    produto_id, fornecedor_id, codigo_fornecedor, preco_custo,
                    prazo_entrega, estoque_fornecedor, e_principal, ativo,
                    tenant_id, created_at, updated_at
                ) VALUES (
                    :product_id, :supplier_id, :supplier_code, :cost,
                    3, 250, true, true, :tenant_id, now(), now()
                )
                """
            ),
            payload,
        )
    return supplier_code


def _confrontation_status(
    ordered_qty: Decimal,
    invoice_qty: Decimal,
    ordered_cost: Decimal,
    invoice_cost: Decimal,
) -> str:
    qty_diff = ordered_qty != invoice_qty
    price_diff = ordered_cost != invoice_cost
    if qty_diff and price_diff:
        return "divergencia_mista"
    if qty_diff:
        return "divergencia_quantidade"
    if price_diff:
        return "divergencia_preco"
    return "sem_divergencia"


def _insert_order(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    product: dict[str, Any],
    number: str,
    status: str,
    ordered_at: datetime,
) -> int:
    order_id = int(
        _scalar(
            db,
            """
            INSERT INTO pedidos_compra (
                numero_pedido, fornecedor_id, status, valor_total, valor_frete,
                valor_desconto, valor_final, data_pedido, data_prevista_entrega,
                data_recebimento, data_envio, data_confirmacao, observacoes,
                foi_alterado_apos_envio, sugestao_ia, confianca_ia, user_id,
                tenant_id, created_at, updated_at
            ) VALUES (
                :number, :supplier_id, :status, 309.40, 0, 0, 309.40,
                :ordered_at, :delivery_at,
                CASE WHEN :status IN ('recebido_parcial', 'recebido_total') THEN :event_at ELSE NULL END,
                CASE WHEN :status <> 'rascunho' THEN :event_at ELSE NULL END,
                CASE WHEN :status IN ('confirmado', 'recebido_parcial', 'recebido_total') THEN :event_at ELSE NULL END,
                'Cenario de demonstracao CorePet - sem valor fiscal.', false, true,
                0.94, :user_id, :tenant_id, :ordered_at, now()
            ) RETURNING id
            """,
            {
                "number": number,
                "supplier_id": supplier_id,
                "status": status,
                "ordered_at": ordered_at,
                "delivery_at": ordered_at + timedelta(days=3),
                "event_at": ordered_at + timedelta(hours=2),
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )
    db.execute(
        text(
            """
            INSERT INTO pedidos_compra_itens (
                pedido_compra_id, produto_id, quantidade_pedida, quantidade_recebida,
                unidade_compra, quantidade_por_embalagem, quantidade_total_unidades,
                preco_unitario, desconto_item, valor_total, status, sugestao_ia,
                motivo_ia, tenant_id, created_at, updated_at
            ) VALUES (
                :order_id, :product_id, 10, 0, 'UN', 1, 10, 30.94, 0, 309.40,
                'pendente', true,
                'Reposicao sugerida pelo giro e pelo estoque minimo do produto.',
                :tenant_id, now(), now()
            )
            """
        ),
        {"order_id": order_id, "product_id": product["id"], "tenant_id": tenant_id},
    )
    return order_id


def _insert_invoice(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    product: dict[str, Any],
    supplier_code: str,
    scenario: dict[str, Any],
    issued_at: datetime,
) -> tuple[int, int]:
    invoice_number = int(scenario["invoice_number"])
    quantity = Decimal(scenario["invoice_qty"])
    unit_cost = Decimal(scenario["invoice_unit_cost"])
    received = Decimal(scenario["received_qty"])
    damaged = Decimal(scenario["damaged_qty"])
    total = quantity * unit_cost
    access_key = _invoice_key(tenant_id, invoice_number)
    conference_status = (
        "sem_divergencia"
        if received == quantity and damaged == 0
        else "com_divergencia"
    )
    xml = _demo_xml(
        invoice_number=invoice_number,
        access_key=access_key,
        issued_at=issued_at,
        supplier_code=supplier_code,
        product_name=str(product["nome"]),
        ean=str(product["ean"]),
        quantity=quantity,
        unit_cost=unit_cost,
    )
    invoice_id = int(
        _scalar(
            db,
            """
            INSERT INTO notas_entrada (
                numero_nota, serie, chave_acesso, fornecedor_cnpj, fornecedor_nome,
                fornecedor_id, data_emissao, data_entrada, valor_produtos,
                valor_frete, valor_desconto, valor_total, xml_content, status,
                conferencia_status, conferencia_observacoes, conferencia_realizada_em,
                conferencia_user_id, produtos_vinculados, produtos_nao_vinculados,
                entrada_estoque_realizada, tipo_rateio, percentual_online,
                percentual_loja, valor_online, valor_loja, user_id, tenant_id,
                created_at, updated_at
            ) VALUES (
                :number, '1', :access_key, :cnpj, 'Distribuidora Pet Brasil Demo LTDA',
                :supplier_id, :issued_at, :entry_at, :total, 0, 0, :total, :xml,
                'pendente', :conference_status, :conference_notes, :entry_at,
                :user_id, 1, 0, false, 'loja', 0, 100, 0, :total,
                :user_id, :tenant_id, :entry_at, now()
            ) RETURNING id
            """,
            {
                "number": str(invoice_number),
                "access_key": access_key,
                "cnpj": DEMO_SUPPLIER_CNPJ,
                "supplier_id": supplier_id,
                "issued_at": issued_at,
                "entry_at": issued_at + timedelta(hours=4),
                "total": total,
                "xml": xml,
                "conference_status": conference_status,
                "conference_notes": (
                    "Recebimento conferido sem diferencas."
                    if conference_status == "sem_divergencia"
                    else "Cenario demo: divergencia identificada na conferencia fisica."
                ),
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )
    item_id = int(
        _scalar(
            db,
            """
            INSERT INTO notas_entrada_itens (
                nota_entrada_id, numero_item, codigo_produto, descricao, ncm, cfop,
                unidade, quantidade, valor_unitario, valor_total, ean, ean_tributario,
                lote, data_validade, produto_id, vinculado, confianca_vinculo, status,
                quantidade_conferida, quantidade_avariada, observacao_conferencia,
                acao_sugerida, quantidade_online, valor_online, tenant_id,
                created_at, updated_at
            ) VALUES (
                :invoice_id, 1, :supplier_code, :description, '23091000', '5102',
                'UN', :quantity, :unit_cost, :total, :ean, :ean,
                :lot, :expires_at, :product_id, true, 1, 'vinculado',
                :received, :damaged, :notes, :suggested_action, 0, 0,
                :tenant_id, now(), now()
            ) RETURNING id
            """,
            {
                "invoice_id": invoice_id,
                "supplier_code": supplier_code,
                "description": product["nome"],
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total": total,
                "ean": product["ean"],
                "lot": f"DEMO-LOTE-{invoice_number}",
                "expires_at": issued_at.date() + timedelta(days=330),
                "product_id": product["id"],
                "received": received,
                "damaged": damaged,
                "notes": (
                    "Conferencia sem divergencias."
                    if conference_status == "sem_divergencia"
                    else "Quantidade fisica diferente da quantidade informada na NF."
                ),
                "suggested_action": (
                    "sem_acao"
                    if conference_status == "sem_divergencia"
                    else "contatar_fornecedor"
                ),
                "tenant_id": tenant_id,
            },
        )
    )
    return invoice_id, item_id


def _link_order_invoice(
    db,
    *,
    tenant_id: str,
    user_id: int,
    order_id: int,
    invoice_id: int,
    status: str,
    scenario: dict[str, Any],
) -> None:
    summary = {
        "demo": True,
        "status_confronto": status,
        "pedido_quantidade": 10,
        "nf_quantidade": float(scenario["invoice_qty"]),
        "pedido_preco": 30.94,
        "nf_preco": float(scenario["invoice_unit_cost"]),
    }
    db.execute(
        text(
            """
            INSERT INTO pedidos_compra_notas_entrada (
                pedido_compra_id, nota_entrada_id, user_id, tenant_id, created_at, updated_at
            ) VALUES (
                :order_id, :invoice_id, :user_id, :tenant_id, now(), now()
            )
            """
        ),
        {
            "order_id": order_id,
            "invoice_id": invoice_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )
    db.execute(
        text(
            """
            UPDATE pedidos_compra
            SET nota_entrada_id = :invoice_id, data_confronto = now(),
                status_confronto = :status, resumo_confronto = :summary,
                confronto_finalizado = true, updated_at = now()
            WHERE id = :order_id
            """
        ),
        {
            "order_id": order_id,
            "invoice_id": invoice_id,
            "status": status,
            "summary": json.dumps(summary, ensure_ascii=False),
        },
    )
    db.execute(
        text(
            """
            UPDATE pedidos_compra_itens
            SET quantidade_recebida = LEAST(quantidade_pedida, :invoice_qty),
                status = CASE
                    WHEN :invoice_qty >= quantidade_pedida THEN 'recebido_total'
                    ELSE 'recebido_parcial'
                END,
                updated_at = now()
            WHERE pedido_compra_id = :order_id
            """
        ),
        {"order_id": order_id, "invoice_qty": scenario["invoice_qty"]},
    )


def _insert_pending(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    product: dict[str, Any],
    order_id: int,
    order_number: str,
    invoice_id: int,
    invoice_item_id: int,
    scenario: dict[str, Any],
    created_at: datetime,
) -> int:
    status = str(scenario["pending_status"])
    quantity = Decimal(scenario["invoice_qty"])
    received = Decimal(scenario["received_qty"])
    damaged = Decimal(scenario["damaged_qty"])
    missing = max(quantity - received - damaged, Decimal("0"))
    divergent_qty = missing + damaged
    unit_cost = Decimal(scenario["invoice_unit_cost"])
    divergent_value = divergent_qty * unit_cost
    final_status = status in {"resolvida", "cancelada"}
    suffix = _tenant_suffix(tenant_id)
    invoice_number = int(scenario["invoice_number"])
    pending_id = int(
        _scalar(
            db,
            """
            INSERT INTO compras_pendencias_fornecedor (
                codigo, status, origem, tipo, fornecedor_id, fornecedor_nome,
                fornecedor_cnpj, nota_entrada_id, pedido_compra_id, numero_nota,
                numero_pedido, titulo, resumo, prazo_previsto, email_destinatario,
                email_assunto, email_mensagem, email_enviado_em, pdf_gerado_em,
                resolvida_em, resolucao_observacao, user_id, tenant_id,
                created_at, updated_at
            ) VALUES (
                :code, :status, 'conferencia_nf', 'divergencia_fornecedor',
                :supplier_id, 'Distribuidora Pet Brasil', :cnpj, :invoice_id,
                :order_id, :invoice_number, :order_number, :title, :summary,
                :due_at, 'compras.demo@corepet.com.br', :subject, :message,
                CASE WHEN :status IN ('aguardando_fornecedor', 'em_tratativa', 'resolvida') THEN :contact_at ELSE NULL END,
                CASE WHEN :status IN ('aguardando_fornecedor', 'em_tratativa', 'resolvida') THEN :contact_at ELSE NULL END,
                CASE WHEN :final_status THEN :resolved_at ELSE NULL END,
                CASE WHEN :status = 'resolvida' THEN 'Credito comercial confirmado pelo fornecedor.'
                     WHEN :status = 'cancelada' THEN 'Divergencia descartada apos nova contagem.'
                     ELSE NULL END,
                :user_id, :tenant_id, :created_at, now()
            ) RETURNING id
            """,
            {
                "code": f"DEMO-PEN-{suffix}-{invoice_number}",
                "status": status,
                "supplier_id": supplier_id,
                "cnpj": DEMO_SUPPLIER_CNPJ,
                "invoice_id": invoice_id,
                "order_id": order_id,
                "invoice_number": str(invoice_number),
                "order_number": order_number,
                "title": f"NF {invoice_number} - {scenario['label']}",
                "summary": (
                    f"1 item com divergencia: {missing:g} faltante(s), "
                    f"{damaged:g} avariada(s), R$ {divergent_value:.2f} estimado."
                ),
                "due_at": created_at + timedelta(days=7),
                "subject": f"Divergencia na NF {invoice_number} - pedido {order_number}",
                "message": (
                    "Ola, Distribuidora Pet Brasil.\n\n"
                    f"Na conferencia da NF {invoice_number}, identificamos diferenca no item "
                    f"{product['nome']}. Foram informadas {quantity:g} unidade(s), recebemos "
                    f"{received:g} e registramos {damaged:g} avariada(s).\n\n"
                    "Pode nos orientar sobre reposicao ou credito?"
                ),
                "contact_at": created_at + timedelta(hours=3),
                "resolved_at": created_at + timedelta(days=2),
                "final_status": final_status,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "created_at": created_at,
            },
        )
    )
    status_item = (
        "falta_avaria" if missing and damaged else "avaria" if damaged else "falta"
    )
    db.execute(
        text(
            """
            INSERT INTO compras_pendencias_fornecedor_itens (
                pendencia_id, nota_entrada_item_id, produto_id, codigo_produto,
                descricao, unidade, quantidade_nf, quantidade_recebida,
                quantidade_faltante, quantidade_avariada, valor_unitario,
                valor_total_divergente, status_conferencia, acao_sugerida,
                observacao, resolvido, tenant_id, created_at, updated_at
            ) VALUES (
                :pending_id, :invoice_item_id, :product_id, :product_code,
                :description, 'UN', :quantity, :received, :missing, :damaged,
                :unit_cost, :divergent_value, :status_item, 'contatar_fornecedor',
                'Cenario sintetico preparado para a demonstracao comercial.',
                :resolved, :tenant_id, :created_at, now()
            )
            """
        ),
        {
            "pending_id": pending_id,
            "invoice_item_id": invoice_item_id,
            "product_id": product["id"],
            "product_code": product["codigo"],
            "description": product["nome"],
            "quantity": quantity,
            "received": received,
            "missing": missing,
            "damaged": damaged,
            "unit_cost": unit_cost,
            "divergent_value": divergent_value,
            "status_item": status_item,
            "resolved": final_status,
            "tenant_id": tenant_id,
            "created_at": created_at,
        },
    )
    history = [("criada", None, "aberta", "Pendencia criada pela conferencia da NF.")]
    if status != "aberta":
        history.append(
            (
                "status_alterado",
                "aberta",
                status,
                f"Cenario atualizado para {scenario['label'].lower()}.",
            )
        )
    for idx, (kind, previous, current, note) in enumerate(history):
        db.execute(
            text(
                """
                INSERT INTO compras_pendencias_fornecedor_historico (
                    pendencia_id, tipo, observacao, status_anterior, status_novo,
                    user_id, tenant_id, created_at, updated_at
                ) VALUES (
                    :pending_id, :kind, :note, :previous, :current,
                    :user_id, :tenant_id, :created_at, now()
                )
                """
            ),
            {
                "pending_id": pending_id,
                "kind": kind,
                "note": note,
                "previous": previous,
                "current": current,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "created_at": created_at + timedelta(hours=idx),
            },
        )
    return pending_id


def insert_demo_purchases(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    base_date: date,
) -> dict[str, Any]:
    product = _purchase_product(db, tenant_id=tenant_id)
    supplier_code = _ensure_product_supplier(
        db,
        tenant_id=tenant_id,
        product=product,
        supplier_id=supplier_id,
    )
    suffix = _tenant_suffix(tenant_id)
    orders = []
    invoices = []
    pendings = []
    ordered_qty = Decimal("10")
    ordered_cost = Decimal("30.94")

    for index, scenario in enumerate(build_demo_purchase_scenarios(), start=1):
        order_number = f"DEMO-PC-{suffix}-{index:03d}"
        ordered_at = datetime.combine(base_date, time(9, 0)) - timedelta(days=8 - index)
        order_id = _insert_order(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=supplier_id,
            product=product,
            number=order_number,
            status=scenario["order_status"],
            ordered_at=ordered_at,
        )
        orders.append(order_id)
        if "invoice_number" not in scenario:
            continue

        invoice_id, invoice_item_id = _insert_invoice(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=supplier_id,
            product=product,
            supplier_code=supplier_code,
            scenario=scenario,
            issued_at=ordered_at + timedelta(days=1),
        )
        invoices.append(invoice_id)
        confrontation_status = _confrontation_status(
            ordered_qty,
            Decimal(scenario["invoice_qty"]),
            ordered_cost,
            Decimal(scenario["invoice_unit_cost"]),
        )
        _link_order_invoice(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            order_id=order_id,
            invoice_id=invoice_id,
            status=confrontation_status,
            scenario=scenario,
        )
        if scenario.get("pending_status"):
            pendings.append(
                _insert_pending(
                    db,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    supplier_id=supplier_id,
                    product=product,
                    order_id=order_id,
                    order_number=order_number,
                    invoice_id=invoice_id,
                    invoice_item_id=invoice_item_id,
                    scenario=scenario,
                    created_at=ordered_at + timedelta(days=1, hours=5),
                )
            )

    return {
        "product_id": int(product["id"]),
        "product_name": product["nome"],
        "supplier_code": supplier_code,
        "orders": orders,
        "invoices": invoices,
        "pendings": pendings,
    }
