"""Data contracts and fixtures for the operational demo seed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


DEFAULT_TARGET_EMAIL = "corepeterp@gmail.com"
DEFAULT_SOURCE_EMAIL = "atacadaopetpp@gmail.com"
PRODUCTION_ENVS = {"prod", "production"}
CENT = Decimal("0.01")
DEFAULT_TAX_PERCENT = Decimal("6.25")
DEFAULT_COMMISSION_PERCENT = Decimal("4.00")
DEMO_PRICE_PROFILES = [
    (Decimal("151.00"), Decimal("239.90")),
    (Decimal("118.00"), Decimal("189.90")),
    (Decimal("104.00"), Decimal("169.90")),
    (Decimal("76.00"), Decimal("129.90")),
    (Decimal("54.00"), Decimal("94.90")),
    (Decimal("43.00"), Decimal("76.90")),
    (Decimal("30.00"), Decimal("59.90")),
    (Decimal("24.90"), Decimal("49.90")),
    (Decimal("17.00"), Decimal("34.90")),
    (Decimal("10.00"), Decimal("24.90")),
    (Decimal("137.00"), Decimal("219.90")),
    (Decimal("88.00"), Decimal("149.90")),
]


@dataclass(frozen=True)
class SaleScenario:
    number: str
    channel: str
    client_key: str
    payment_key: str
    items: tuple[tuple[int, Decimal], ...]
    days_ago: int
    due_in_days: int = 0
    discount_value: Decimal = Decimal("0")
    discount_percent: Decimal = Decimal("0")
    coupon: str | None = None
    delivery: bool = False
    delivery_fee: Decimal = Decimal("0")
    driver_share: Decimal = Decimal("0")
    delivery_km: Decimal = Decimal("0")
    route_number: str | None = None
    route_status: str | None = None
    received_ratio: Decimal = Decimal("1")
    installments: int = 1
    card_brand: str | None = None
    order_id: str | None = None
    order_origin: str | None = None
    order_status: str | None = None
    commissioned: bool = False
    observations: str = ""


@dataclass(frozen=True)
class FixedPayable:
    document: str
    description: str
    category_key: str
    amount: Decimal
    days_ago: int
    due_in_days: int
    paid: bool
    supplier_key: str
    channel: str | None = None


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def decimal_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def build_demo_scenarios() -> list[SaleScenario]:
    """Return the sales path Lucas wants visible in the demo."""

    return [
        SaleScenario(
            number="DEMO-VEN-001",
            channel="loja_fisica",
            client_key="ana",
            payment_key="pix",
            items=((0, Decimal("1")), (1, Decimal("2"))),
            days_ago=1,
            observations="Venda balcão sem desconto, baixa imediata no PIX.",
            commissioned=True,
        ),
        SaleScenario(
            number="DEMO-VEN-002",
            channel="loja_fisica",
            client_key="joao",
            payment_key="debito",
            items=((2, Decimal("1")), (3, Decimal("1"))),
            days_ago=3,
            due_in_days=1,
            discount_value=Decimal("12.00"),
            delivery=True,
            delivery_fee=Decimal("18.00"),
            driver_share=Decimal("12.00"),
            delivery_km=Decimal("6.4"),
            route_number="DEMO-ROT-001",
            route_status="concluida",
            card_brand="visa",
            observations="Venda balcão com entrega, desconto e débito recebido.",
            commissioned=True,
        ),
        SaleScenario(
            number="DEMO-VEN-003",
            channel="app_mobile",
            client_key="maria",
            payment_key="credito",
            items=((0, Decimal("1")), (4, Decimal("2"))),
            days_ago=5,
            due_in_days=12,
            discount_percent=Decimal("10.00"),
            coupon="APP10",
            delivery=True,
            delivery_fee=Decimal("14.00"),
            driver_share=Decimal("9.00"),
            delivery_km=Decimal("4.2"),
            route_number="DEMO-ROT-002",
            route_status="em_rota",
            received_ratio=Decimal("0.40"),
            installments=3,
            card_brand="master",
            order_id="DEMO-APP-001",
            order_origin="app",
            order_status="em_preparo",
            observations="Venda pelo app com campanha, cartão parcelado e baixa parcial.",
            commissioned=True,
        ),
        SaleScenario(
            number="DEMO-VEN-004",
            channel="ecommerce",
            client_key="ana",
            payment_key="credito",
            items=((1, Decimal("1")), (5, Decimal("1"))),
            days_ago=2,
            due_in_days=18,
            delivery=True,
            delivery_fee=Decimal("22.00"),
            driver_share=Decimal("14.00"),
            delivery_km=Decimal("9.1"),
            route_number="DEMO-ROT-003",
            route_status="pendente",
            received_ratio=Decimal("0"),
            installments=2,
            card_brand="elo",
            order_id="DEMO-ECO-001",
            order_origin="web",
            order_status="aguardando_pagamento",
            observations="Pedido e-commerce com previsão de recebimento futura.",
        ),
        SaleScenario(
            number="DEMO-VEN-005",
            channel="loja_fisica",
            client_key="distribuidora",
            payment_key="dinheiro",
            items=((3, Decimal("3")),),
            days_ago=8,
            discount_value=Decimal("5.00"),
            observations="Venda no dinheiro com desconto manual e baixa total.",
        ),
        SaleScenario(
            number="DEMO-VEN-006",
            channel="app_mobile",
            client_key="joao",
            payment_key="pix",
            items=((2, Decimal("2")), (0, Decimal("1"))),
            days_ago=10,
            coupon="FIDELIDADE5",
            discount_value=Decimal("8.00"),
            order_id="DEMO-APP-002",
            order_origin="app",
            order_status="entregue",
            observations="Venda pelo app com campanha de fidelidade e retirada.",
            commissioned=True,
        ),
    ]


def build_fixed_payables() -> list[FixedPayable]:
    return [
        FixedPayable(
            document="DEMO-CP-COMPRA-001",
            description="Demo operacional - Compra de mercadorias para reposicao",
            category_key="compra_mercadorias",
            amount=Decimal("1450.00"),
            days_ago=12,
            due_in_days=0,
            paid=True,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-FOLHA-001",
            description="Demo operacional - Folha RH equipe de loja",
            category_key="folha_operacional",
            amount=Decimal("3650.00"),
            days_ago=6,
            due_in_days=0,
            paid=True,
            supplier_key="funcionario_vendedor",
            channel="loja_fisica",
        ),
        FixedPayable(
            document="DEMO-CP-ALUGUEL-001",
            description="Demo operacional - Aluguel da loja",
            category_key="aluguel_loja",
            amount=Decimal("1850.00"),
            days_ago=7,
            due_in_days=0,
            paid=True,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-ENERGIA-001",
            description="Demo operacional - Energia eletrica prevista",
            category_key="energia",
            amount=Decimal("420.00"),
            days_ago=1,
            due_in_days=2,
            paid=False,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-IMPOSTO-001",
            description="Demo operacional - Simples Nacional previsto",
            category_key="impostos",
            amount=Decimal("680.00"),
            days_ago=1,
            due_in_days=8,
            paid=False,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-COMISSAO-BASE",
            description="Demo operacional - Comissao de vendas prevista",
            category_key="comissoes_vendas",
            amount=Decimal("180.00"),
            days_ago=1,
            due_in_days=7,
            paid=False,
            supplier_key="funcionario_vendedor",
            channel="loja_fisica",
        ),
        FixedPayable(
            document="DEMO-CP-MKT-001",
            description="Demo operacional - Campanhas e criativos",
            category_key="marketing",
            amount=Decimal("300.00"),
            days_ago=4,
            due_in_days=0,
            paid=True,
            supplier_key="fornecedor",
            channel="ecommerce",
        ),
    ]
