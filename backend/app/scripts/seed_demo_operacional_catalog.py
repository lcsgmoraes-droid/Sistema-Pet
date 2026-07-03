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


def _cleanup_previous_demo(db, *, tenant_id: str) -> None:
    params = {"tenant_id": tenant_id}
    statements = [
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
        "DELETE FROM caixas WHERE tenant_id = :tenant_id AND observacoes_abertura LIKE 'Demo operacional%'",
    ]
    for sql in statements:
        db.execute(text(sql), params)


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
              AND codigo ILIKE 'DEMO-%'
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
