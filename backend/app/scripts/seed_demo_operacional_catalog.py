"""Catalog and product helpers for the operational demo seed."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_data import (
    DEMO_PRICE_PROFILES,
    SaleScenario,
    money,
)
from app.scripts.seed_demo_operacional_db import _all_mappings, _scalar


DEMO_MARGIN_PRODUCTS = (
    {
        "code": "DEMO-MARGEM-VERDE",
        "name": "Demo PDV - Margem saudavel",
        "cost": Decimal("45.00"),
        "price": Decimal("100.00"),
        "stock": Decimal("30"),
        "minimum_stock": Decimal("5"),
    },
    {
        "code": "DEMO-MARGEM-AMARELA",
        "name": "Demo PDV - Margem em alerta",
        "cost": Decimal("69.50"),
        "price": Decimal("100.00"),
        "stock": Decimal("20"),
        "minimum_stock": Decimal("5"),
    },
    {
        "code": "DEMO-MARGEM-VERMELHA",
        "name": "Demo PDV - Margem critica",
        "cost": Decimal("82.00"),
        "price": Decimal("100.00"),
        "stock": Decimal("8"),
        "minimum_stock": Decimal("12"),
    },
)


def _cleanup_previous_demo(db, *, tenant_id: str) -> None:
    params = {"tenant_id": tenant_id}
    statements = [
        "DELETE FROM conciliacao_importacoes WHERE tenant_id = :tenant_id AND resumo->>'demo_operacional' = 'true'",
        "DELETE FROM arquivos_evidencia WHERE tenant_id = :tenant_id AND caminho_storage = 'demo://conciliacao/stone-vendas.csv'",
        "DELETE FROM alertas_estoque_negativo WHERE tenant_id = :tenant_id AND observacao LIKE 'Demo operacional%'",
        "DELETE FROM compras_pendencias_fornecedor_historico WHERE tenant_id = :tenant_id AND pendencia_id IN (SELECT id FROM compras_pendencias_fornecedor WHERE tenant_id = :tenant_id AND codigo LIKE 'DEMO-PEN-%')",
        "DELETE FROM compras_pendencias_fornecedor_itens WHERE tenant_id = :tenant_id AND pendencia_id IN (SELECT id FROM compras_pendencias_fornecedor WHERE tenant_id = :tenant_id AND codigo LIKE 'DEMO-PEN-%')",
        "DELETE FROM compras_pendencias_fornecedor WHERE tenant_id = :tenant_id AND codigo LIKE 'DEMO-PEN-%'",
        "DELETE FROM pedidos_compra_notas_entrada WHERE tenant_id = :tenant_id AND (pedido_compra_id IN (SELECT id FROM pedidos_compra WHERE tenant_id = :tenant_id AND numero_pedido LIKE 'DEMO-PC-%') OR nota_entrada_id IN (SELECT id FROM notas_entrada WHERE tenant_id = :tenant_id AND xml_content LIKE '%DOCUMENTO SINTETICO PARA DEMONSTRACAO DO COREPET%'))",
        "DELETE FROM pedidos_compra_itens WHERE tenant_id = :tenant_id AND pedido_compra_id IN (SELECT id FROM pedidos_compra WHERE tenant_id = :tenant_id AND numero_pedido LIKE 'DEMO-PC-%')",
        "DELETE FROM pedidos_compra WHERE tenant_id = :tenant_id AND numero_pedido LIKE 'DEMO-PC-%'",
        "DELETE FROM notas_entrada_itens WHERE tenant_id = :tenant_id AND nota_entrada_id IN (SELECT id FROM notas_entrada WHERE tenant_id = :tenant_id AND xml_content LIKE '%DOCUMENTO SINTETICO PARA DEMONSTRACAO DO COREPET%')",
        "DELETE FROM notas_entrada WHERE tenant_id = :tenant_id AND xml_content LIKE '%DOCUMENTO SINTETICO PARA DEMONSTRACAO DO COREPET%'",
        "DELETE FROM comissoes_vendas WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM comissoes_itens WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM movimentacoes_bancarias WHERE tenant_id = :tenant_id AND (fitid LIKE 'DEMO-%' OR memo LIKE 'Demo operacional%')",
        "DELETE FROM movimentacoes_financeiras WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR descricao LIKE 'Demo operacional%')",
        "DELETE FROM fluxo_caixa WHERE tenant_id = :tenant_id AND (descricao LIKE 'Demo operacional%' OR origem_tipo = 'demo_operacional')",
        "DELETE FROM pagamentos WHERE tenant_id = :tenant_id AND conta_pagar_id IN (SELECT id FROM contas_pagar WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%')",
        "DELETE FROM recebimentos WHERE tenant_id = :tenant_id AND conta_receber_id IN (SELECT id FROM contas_receber WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')))",
        "DELETE FROM rotas_entrega_paradas WHERE tenant_id = :tenant_id AND (rota_id IN (SELECT id FROM rotas_entrega WHERE tenant_id = :tenant_id AND numero LIKE 'DEMO-ROT-%') OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM rotas_entrega WHERE tenant_id = :tenant_id AND (numero LIKE 'DEMO-ROT-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM pedido_itens WHERE tenant_id = :tenant_id AND pedido_id LIKE 'DEMO-%'",
        "DELETE FROM pedidos WHERE tenant_id = :tenant_id AND pedido_id LIKE 'DEMO-%'",
        "DELETE FROM contas_pagar WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'",
        "DELETE FROM contas_receber WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM venda_baixas WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM venda_pagamentos WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM venda_itens WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM movimentacoes_caixa WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'",
        "DELETE FROM estoque_movimentacoes WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'",
        """
        DELETE FROM caixas c
        WHERE c.tenant_id = :tenant_id
          AND c.observacoes_abertura LIKE 'Demo operacional%'
          AND NOT EXISTS (SELECT 1 FROM vendas v WHERE v.caixa_id = c.id)
          AND NOT EXISTS (SELECT 1 FROM movimentacoes_caixa m WHERE m.caixa_id = c.id)
        """,
    ]
    for sql in statements:
        db.execute(text(sql), params)


def _ensure_demo_stock_alerts(
    db,
    *,
    tenant_id: str,
    user_id: int,
    product_ids: dict[str, int],
) -> list[int]:
    """Create persistent stock-alert states for the presentation filters."""

    scenarios = (
        {
            "code": "DEMO-MARGEM-VERMELHA",
            "previous": 3,
            "sold": 5,
            "result": -2,
            "status": "pendente",
            "resolved_expression": "NULL",
            "critical": False,
            "note": "Demo operacional - alerta pendente aguardando reposicao.",
        },
        {
            "code": "DEMO-MARGEM-AMARELA",
            "previous": 2,
            "sold": 4,
            "result": -2,
            "status": "resolvido",
            "resolved_expression": "now() - interval '1 day'",
            "critical": False,
            "note": "Demo operacional - alerta resolvido com entrada de estoque.",
        },
        {
            "code": "DEMO-MARGEM-VERDE",
            "previous": 1,
            "sold": 8,
            "result": -7,
            "status": "ignorado",
            "resolved_expression": "now() - interval '2 days'",
            "critical": True,
            "note": "Demo operacional - alerta ignorado apos conferencia manual.",
        },
    )
    ids: list[int] = []
    for scenario in scenarios:
        alert_id = _scalar(
            db,
            f"""
            INSERT INTO alertas_estoque_negativo (
                produto_id, produto_nome, estoque_anterior, quantidade_vendida,
                estoque_resultante, data_alerta, status, data_resolucao,
                usuario_resolucao_id, observacao, notificado, critico,
                tenant_id, created_at, updated_at
            )
            SELECT id, nome, :previous, :sold, :result,
                   now() - interval '3 days', :status,
                   {scenario["resolved_expression"]},
                   CASE WHEN :status = 'pendente' THEN NULL ELSE :user_id END,
                   :note, true, :critical, :tenant_id, now(), now()
            FROM produtos
            WHERE tenant_id = :tenant_id AND id = :product_id
            RETURNING id
            """,
            {
                **scenario,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "product_id": product_ids[scenario["code"]],
            },
        )
        ids.append(int(alert_id))
    return ids


def _ensure_demo_product_category(db, *, tenant_id: str, user_id: int) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM categorias
        WHERE tenant_id = :tenant_id AND lower(nome) = lower('Racoes Demo')
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if existing:
        return int(existing)
    return int(
        _scalar(
            db,
            """
            INSERT INTO categorias (
                nome, descricao, cor, icone, ativo, user_id, tenant_id,
                created_at, updated_at
            )
            VALUES (
                'Racoes Demo', 'Categoria fallback para demo operacional',
                '#0F766E', 'package', true, :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {"tenant_id": tenant_id, "user_id": user_id},
        )
    )


def _ensure_fallback_products(db, *, tenant_id: str, user_id: int) -> None:
    count = _scalar(
        db,
        """
        SELECT count(*) FROM produtos
        WHERE tenant_id = :tenant_id AND COALESCE(ativo, true) = true
          AND COALESCE(is_sellable, true) = true
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id},
    )
    if int(count or 0) >= 4:
        return

    category_id = _ensure_demo_product_category(
        db, tenant_id=tenant_id, user_id=user_id
    )
    products = [
        (
            "DEMO-RACAO-10KG",
            "Racao Premium Adulto 10kg",
            Decimal("128.00"),
            Decimal("189.90"),
        ),
        (
            "DEMO-RACAO-FILHOTE",
            "Racao Filhote Frango 3kg",
            Decimal("42.00"),
            Decimal("69.90"),
        ),
        (
            "DEMO-PETISCO-120G",
            "Petisco Natural 120g",
            Decimal("10.00"),
            Decimal("24.90"),
        ),
        (
            "DEMO-SHAMPOO-500ML",
            "Shampoo Neutro 500ml",
            Decimal("18.00"),
            Decimal("39.90"),
        ),
        ("DEMO-COLEIRA-M", "Coleira Ajustavel M", Decimal("22.00"), Decimal("49.90")),
        ("DEMO-AREIA-4KG", "Areia Higienica 4kg", Decimal("16.00"), Decimal("32.90")),
    ]
    for code, name, cost, price in products:
        exists = _scalar(
            db,
            """
            SELECT id FROM produtos
            WHERE tenant_id = :tenant_id AND lower(trim(codigo)) = lower(:code)
            LIMIT 1
            """,
            {"tenant_id": tenant_id, "code": code},
        )
        if exists:
            continue
        db.execute(
            text(
                """
                INSERT INTO produtos (
                    codigo, nome, tipo, situacao, tipo_produto, is_parent,
                    is_sellable, categoria_id, preco_custo, preco_venda,
                    preco_ecommerce, preco_app, estoque_atual, estoque_minimo,
                    estoque_fisico, estoque_ecommerce, unidade, classificacao_racao,
                    categoria_racao, peso_embalagem, auto_classificar_nome,
                    anunciar_ecommerce, anunciar_app, ativo, user_id, tenant_id,
                    created_at, updated_at
                )
                VALUES (
                    :code, :name, 'produto', true, 'SIMPLES', false,
                    true, :category_id, :cost, :price,
                    :price, :price, 30, 5,
                    24, 6, 'UN', 'premium',
                    'cao', 10, true,
                    true, true, true, :user_id, :tenant_id,
                    now(), now()
                )
                """
            ),
            {
                "code": code,
                "name": name,
                "category_id": category_id,
                "cost": cost,
                "price": price,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )


def _ensure_margin_demo_products(db, *, tenant_id: str, user_id: int) -> dict[str, int]:
    """Prepare stable products for the green/yellow/red PDV margin demo."""

    category_id = _ensure_demo_product_category(
        db, tenant_id=tenant_id, user_id=user_id
    )
    result: dict[str, int] = {}
    for product in DEMO_MARGIN_PRODUCTS:
        existing = _scalar(
            db,
            """
            SELECT id FROM produtos
            WHERE tenant_id = :tenant_id AND lower(trim(codigo)) = lower(:code)
            LIMIT 1
            """,
            {"tenant_id": tenant_id, "code": product["code"]},
        )
        payload = {
            **product,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "category_id": category_id,
        }
        if existing:
            db.execute(
                text(
                    """
                    UPDATE produtos
                    SET nome = :name,
                        categoria_id = :category_id,
                        preco_custo = :cost,
                        preco_venda = :price,
                        preco_ecommerce = :price,
                        preco_app = :price,
                        estoque_atual = :stock,
                        estoque_fisico = :stock,
                        estoque_ecommerce = 0,
                        estoque_minimo = :minimum_stock,
                        is_sellable = true,
                        ativo = true,
                        anunciar_ecommerce = false,
                        anunciar_app = false,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {**payload, "id": existing},
            )
            result[product["code"]] = int(existing)
            continue

        product_id = _scalar(
            db,
            """
            INSERT INTO produtos (
                codigo, nome, tipo, situacao, tipo_produto, is_parent,
                is_sellable, categoria_id, preco_custo, preco_venda,
                preco_ecommerce, preco_app, estoque_atual, estoque_minimo,
                estoque_fisico, estoque_ecommerce, unidade,
                classificacao_racao, categoria_racao, peso_embalagem,
                auto_classificar_nome,
                anunciar_ecommerce, anunciar_app, ativo, user_id, tenant_id,
                created_at, updated_at
            )
            VALUES (
                :code, :name, 'produto', true, 'SIMPLES', false,
                true, :category_id, :cost, :price,
                :price, :price, :stock, :minimum_stock,
                :stock, 0, 'UN',
                'nao_aplicavel', 'demo', 0, false,
                false, false, true, :user_id, :tenant_id,
                now(), now()
            )
            RETURNING id
            """,
            payload,
        )
        result[product["code"]] = int(product_id)

    return result


def _has_enough_real_products(db, *, tenant_id: str) -> bool:
    count = _scalar(
        db,
        """
        SELECT count(*) FROM produtos
        WHERE tenant_id = :tenant_id
          AND COALESCE(ativo, true) = true
          AND COALESCE(is_sellable, true) = true
          AND deleted_at IS NULL
          AND COALESCE(tipo_produto, 'SIMPLES') <> 'PAI'
          AND codigo NOT ILIKE 'DEMO-%'
        """,
        {"tenant_id": tenant_id},
    )
    return int(count or 0) >= 4


def _deactivate_demo_fallback_products(db, *, tenant_id: str) -> None:
    db.execute(
        text(
            """
            UPDATE produtos
            SET ativo = false,
                anunciar_ecommerce = false,
                anunciar_app = false,
                updated_at = now()
            WHERE tenant_id = :tenant_id
              AND codigo IN (
                'DEMO-RACAO-10KG', 'DEMO-RACAO-FILHOTE',
                'DEMO-PETISCO-120G', 'DEMO-SHAMPOO-500ML',
                'DEMO-COLEIRA-M', 'DEMO-AREIA-4KG'
              )
            """
        ),
        {"tenant_id": tenant_id},
    )


def _extract_package_weight_kg(name: str) -> Decimal | None:
    match = re.search(r"(\d+(?:[,.]\d+)?)\s*(kg|kilo|g|gr)\b", name.lower())
    if not match:
        return None

    amount = Decimal(match.group(1).replace(",", "."))
    unit = match.group(2)
    if unit in {"g", "gr"}:
        return money(amount / Decimal("1000"))
    return money(amount)


def _demo_price_profile_for_product(
    product: dict[str, Any], idx: int
) -> tuple[Decimal, Decimal]:
    name = str(product.get("nome") or "")
    normalized_name = name.lower()
    weight_kg = _extract_package_weight_kg(name)
    is_ration = "racao" in normalized_name or "ração" in normalized_name

    if is_ration and weight_kg:
        if weight_kg >= Decimal("18"):
            prices = [Decimal("219.90"), Decimal("239.90"), Decimal("249.90")]
        elif weight_kg >= Decimal("14"):
            prices = [Decimal("169.90"), Decimal("189.90"), Decimal("199.90")]
        elif weight_kg >= Decimal("10"):
            prices = [Decimal("129.90"), Decimal("149.90"), Decimal("159.90")]
        elif weight_kg >= Decimal("5"):
            prices = [Decimal("89.90"), Decimal("99.90"), Decimal("109.90")]
        elif weight_kg >= Decimal("2"):
            prices = [Decimal("44.90"), Decimal("49.90"), Decimal("59.90")]
        else:
            prices = [Decimal("24.90"), Decimal("29.90"), Decimal("34.90")]
        price = prices[idx % len(prices)]
        return money(price * Decimal("0.62")), money(price)

    if weight_kg and weight_kg < Decimal("1"):
        prices = [
            Decimal("19.90"),
            Decimal("24.90"),
            Decimal("34.90"),
            Decimal("49.90"),
        ]
        price = prices[idx % len(prices)]
        return money(price * Decimal("0.48")), money(price)

    cost, price = DEMO_PRICE_PROFILES[idx % len(DEMO_PRICE_PROFILES)]
    return money(cost), money(price)


def _product_pool(db, *, tenant_id: str, user_id: int) -> list[dict[str, Any]]:
    _ensure_fallback_products(db, tenant_id=tenant_id, user_id=user_id)
    has_real_catalog = _has_enough_real_products(db, tenant_id=tenant_id)
    if has_real_catalog:
        _deactivate_demo_fallback_products(db, tenant_id=tenant_id)
    real_product_filter = "AND codigo NOT ILIKE 'DEMO-%'" if has_real_catalog else ""
    products = _all_mappings(
        db,
        f"""
        SELECT id, codigo, nome,
               COALESCE(NULLIF(preco_venda, 0), NULLIF(preco_app, 0), NULLIF(preco_ecommerce, 0), 49.90) AS preco_venda,
               COALESCE(NULLIF(preco_custo, 0), 24.90) AS preco_custo,
               COALESCE(estoque_atual, 0) AS estoque_atual
        FROM produtos
        WHERE tenant_id = :tenant_id
          AND COALESCE(ativo, true) = true
          AND COALESCE(is_sellable, true) = true
          AND deleted_at IS NULL
          AND COALESCE(tipo_produto, 'SIMPLES') <> 'PAI'
          {real_product_filter}
        ORDER BY
          CASE
            WHEN nome ILIKE '%racao%' OR nome ILIKE '%ração%' OR classificacao_racao IS NOT NULL OR categoria_racao IS NOT NULL THEN 0
            ELSE 1
          END,
          nome,
          id
        LIMIT 50
        """,
        {"tenant_id": tenant_id},
    )
    for idx, product in enumerate(products):
        cost, price = _demo_price_profile_for_product(product, idx)
        final_cost = money(cost)
        final_price = money(price)
        baseline = Decimal("32") + Decimal(idx * 4)
        db.execute(
            text(
                """
                UPDATE produtos
                SET preco_custo = :cost,
                    preco_venda = :price,
                    preco_ecommerce = COALESCE(preco_ecommerce, :price),
                    preco_app = COALESCE(preco_app, :price),
                    estoque_atual = :baseline,
                    estoque_fisico = :fisico,
                    estoque_ecommerce = :ecommerce,
                    anunciar_ecommerce = true,
                    anunciar_app = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": product["id"],
                "cost": final_cost,
                "price": final_price,
                "baseline": baseline,
                "fisico": baseline - Decimal("8"),
                "ecommerce": Decimal("8"),
            },
        )
        product["preco_custo"] = final_cost
        product["preco_venda"] = final_price
        product["baseline"] = baseline
        product["sold_qty"] = Decimal("0")
    return products


def _sale_items(
    products: list[dict[str, Any]], scenario: SaleScenario
) -> list[dict[str, Any]]:
    items = []
    for idx, qty in scenario.items:
        product = products[idx % len(products)]
        unit_price = money(product["preco_venda"])
        subtotal = money(unit_price * qty)
        items.append(
            {
                "product": product,
                "qty": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    return items
