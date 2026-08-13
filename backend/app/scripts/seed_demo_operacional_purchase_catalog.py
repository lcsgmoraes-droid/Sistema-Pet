"""Catalogo ficticio usado no fluxo de pedido inteligente do tenant Demo."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_catalog import _ensure_demo_product_category
from app.scripts.seed_demo_operacional_data import money
from app.scripts.seed_demo_operacional_db import _scalar


DEMO_PURCHASE_BRAND = "VivaPata Demo"
DEMO_PURCHASE_PRODUCTS = (
    {
        "code": "DEMO-VP-001",
        "supplier_code": "HORIZONTE-001",
        "barcode": "2999999900001",
        "name": "Ração VivaPata Essencial Cães Adultos Frango 10 kg",
        "cost": Decimal("30.94"),
        "price": Decimal("87.40"),
        "stock": Decimal("46"),
        "minimum_stock": Decimal("18"),
        "lead_time": 3,
    },
    {
        "code": "DEMO-VP-002",
        "supplier_code": "HORIZONTE-002",
        "barcode": "2999999900002",
        "name": "Ração VivaPata Select Cães Pequenos Carne 3 kg",
        "cost": Decimal("22.17"),
        "price": Decimal("64.80"),
        "stock": Decimal("50"),
        "minimum_stock": Decimal("16"),
        "lead_time": 3,
    },
    {
        "code": "DEMO-VP-003",
        "supplier_code": "HORIZONTE-003",
        "barcode": "2999999900003",
        "name": "Ração VivaPata Prime Filhotes Frango e Arroz 10 kg",
        "cost": Decimal("47.63"),
        "price": Decimal("118.20"),
        "stock": Decimal("28"),
        "minimum_stock": Decimal("14"),
        "lead_time": 4,
    },
    {
        "code": "DEMO-VP-004",
        "supplier_code": "HORIZONTE-004",
        "barcode": "2999999900004",
        "name": "Ração VivaPata Gatos Castrados Salmão 7 kg",
        "cost": Decimal("39.28"),
        "price": Decimal("96.70"),
        "stock": Decimal("30"),
        "minimum_stock": Decimal("15"),
        "lead_time": 4,
    },
    {
        "code": "DEMO-VP-005",
        "supplier_code": "HORIZONTE-005",
        "barcode": "2999999900005",
        "name": "Ração VivaPata Gatos Adultos Frango 3 kg",
        "cost": Decimal("18.76"),
        "price": Decimal("58.30"),
        "stock": Decimal("24"),
        "minimum_stock": Decimal("12"),
        "lead_time": 2,
    },
    {
        "code": "DEMO-VP-006",
        "supplier_code": "HORIZONTE-006",
        "barcode": "2999999900006",
        "name": "VivaPata Petisco Crocante Frango 500 g",
        "cost": Decimal("8.43"),
        "price": Decimal("27.60"),
        "stock": Decimal("28"),
        "minimum_stock": Decimal("12"),
        "lead_time": 2,
    },
    {
        "code": "DEMO-VP-007",
        "supplier_code": "HORIZONTE-007",
        "barcode": "2999999900007",
        "name": "VivaPata Petisco Dental Menta 300 g",
        "cost": Decimal("7.12"),
        "price": Decimal("24.90"),
        "stock": Decimal("20"),
        "minimum_stock": Decimal("10"),
        "lead_time": 2,
    },
    {
        "code": "DEMO-VP-008",
        "supplier_code": "HORIZONTE-008",
        "barcode": "2999999900008",
        "name": "Sachê VivaPata Cães Carne 100 g",
        "cost": Decimal("1.37"),
        "price": Decimal("6.80"),
        "stock": Decimal("28"),
        "minimum_stock": Decimal("20"),
        "lead_time": 2,
    },
    {
        "code": "DEMO-VP-009",
        "supplier_code": "HORIZONTE-009",
        "barcode": "2999999900009",
        "name": "Sachê VivaPata Gatos Salmão 85 g",
        "cost": Decimal("1.19"),
        "price": Decimal("6.40"),
        "stock": Decimal("24"),
        "minimum_stock": Decimal("20"),
        "lead_time": 2,
    },
    {
        "code": "DEMO-VP-010",
        "supplier_code": "HORIZONTE-010",
        "barcode": "2999999900010",
        "name": "VivaPata Biscoito Integral 400 g",
        "cost": Decimal("5.86"),
        "price": Decimal("21.30"),
        "stock": Decimal("28"),
        "minimum_stock": Decimal("12"),
        "lead_time": 3,
    },
)


def _ensure_demo_purchase_brand(db, *, tenant_id: str, user_id: int) -> int:
    brand_id = _scalar(
        db,
        """
        SELECT id FROM marcas
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        ORDER BY id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": DEMO_PURCHASE_BRAND},
    )
    if brand_id:
        db.execute(
            text(
                """
                UPDATE marcas
                SET descricao = 'Marca ficticia para demonstracoes do CorePet',
                    ativo = true, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :brand_id
                """
            ),
            {"tenant_id": tenant_id, "brand_id": int(brand_id)},
        )
        return int(brand_id)

    return int(
        _scalar(
            db,
            """
            INSERT INTO marcas (
                nome, descricao, user_id, ativo, tenant_id, created_at, updated_at
            ) VALUES (
                :name, 'Marca ficticia para demonstracoes do CorePet',
                :user_id, true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "name": DEMO_PURCHASE_BRAND,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _upsert_demo_purchase_product(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    category_id: int,
    brand_id: int,
    product: dict[str, Any],
) -> int:
    product_id = _scalar(
        db,
        """
        SELECT id FROM produtos
        WHERE tenant_id = :tenant_id AND lower(trim(codigo)) = lower(:code)
        ORDER BY id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "code": product["code"]},
    )
    payload = {
        **product,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "supplier_id": supplier_id,
        "category_id": category_id,
        "brand_id": brand_id,
    }

    if product_id:
        db.execute(
            text(
                """
                UPDATE produtos
                SET nome = :name, codigo_barras = :barcode,
                    gtin_ean = :barcode, gtin_ean_tributario = :barcode,
                    categoria_id = :category_id, marca_id = :brand_id,
                    fornecedor_id = :supplier_id,
                    preco_custo = :cost, preco_venda = :price,
                    preco_ecommerce = :price, preco_app = :price,
                    estoque_atual = :stock, estoque_minimo = :minimum_stock,
                    estoque_fisico = :stock, estoque_ecommerce = 0,
                    unidade = 'UN', situacao = true, ativo = true,
                    tipo = 'produto', tipo_produto = 'SIMPLES',
                    is_parent = false, is_sellable = true,
                    auto_classificar_nome = false,
                    e_granel = false, participa_sugestao_compra = true,
                    anunciar_ecommerce = false, anunciar_app = false,
                    descricao_curta = 'Produto ficticio para demonstracao do CorePet.',
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :product_id
                """
            ),
            {**payload, "product_id": int(product_id)},
        )
        return int(product_id)

    return int(
        _scalar(
            db,
            """
            INSERT INTO produtos (
                codigo, nome, tipo, situacao, tipo_produto, is_parent,
                is_sellable, descricao_curta, codigo_barras, categoria_id,
                marca_id, fornecedor_id, preco_custo, preco_venda,
                preco_ecommerce, preco_app, estoque_atual, estoque_minimo,
                estoque_fisico, estoque_ecommerce, unidade, e_granel,
                participa_sugestao_compra, auto_classificar_nome,
                anunciar_ecommerce, anunciar_app, ativo,
                gtin_ean, gtin_ean_tributario, user_id, tenant_id,
                created_at, updated_at
            ) VALUES (
                :code, :name, 'produto', true, 'SIMPLES', false,
                true, 'Produto ficticio para demonstracao do CorePet.',
                :barcode, :category_id, :brand_id, :supplier_id,
                :cost, :price, :price, :price, :stock, :minimum_stock,
                :stock, 0, 'UN', false, true, false,
                false, false, true, :barcode, :barcode,
                :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            payload,
        )
    )


def ensure_demo_purchase_catalog(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
) -> list[dict[str, Any]]:
    """Cria a linha ficticia e a devolve pronta para gerar historico de vendas."""

    category_id = _ensure_demo_product_category(
        db, tenant_id=tenant_id, user_id=user_id
    )
    brand_id = _ensure_demo_purchase_brand(db, tenant_id=tenant_id, user_id=user_id)

    # O fornecedor DEMO e exclusivo deste roteiro. Ao recriar a carga, removemos
    # vinculos antigos com itens reais para que nenhum nome real apareca no video.
    db.execute(
        text(
            """
            DELETE FROM produto_fornecedores
            WHERE tenant_id = :tenant_id AND fornecedor_id = :supplier_id
            """
        ),
        {"tenant_id": tenant_id, "supplier_id": supplier_id},
    )
    db.execute(
        text(
            """
            UPDATE produtos
            SET fornecedor_id = NULL, updated_at = now()
            WHERE tenant_id = :tenant_id AND fornecedor_id = :supplier_id
              AND codigo NOT LIKE 'DEMO-VP-%'
            """
        ),
        {"tenant_id": tenant_id, "supplier_id": supplier_id},
    )

    result = []
    for product in DEMO_PURCHASE_PRODUCTS:
        product_id = _upsert_demo_purchase_product(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=supplier_id,
            category_id=category_id,
            brand_id=brand_id,
            product=product,
        )
        db.execute(
            text(
                """
                INSERT INTO produto_fornecedores (
                    produto_id, fornecedor_id, codigo_fornecedor, preco_custo,
                    prazo_entrega, estoque_fornecedor, e_principal, ativo,
                    tenant_id, created_at, updated_at
                ) VALUES (
                    :product_id, :supplier_id, :supplier_code, :cost,
                    :lead_time, 400, true, true, :tenant_id, now(), now()
                )
                """
            ),
            {
                **product,
                "product_id": product_id,
                "supplier_id": supplier_id,
                "tenant_id": tenant_id,
            },
        )
        result.append(
            {
                "id": product_id,
                "codigo": product["code"],
                "nome": product["name"],
                "preco_custo": money(product["cost"]),
                "preco_venda": money(product["price"]),
                "estoque_atual": money(product["stock"]),
                "baseline": money(product["stock"]),
                "sold_qty": Decimal("0"),
            }
        )

    return result
