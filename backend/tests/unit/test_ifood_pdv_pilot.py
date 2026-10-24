"""Contrato e isolamento do piloto DEV: nenhuma chamada ao iFood."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.config import settings
from app.models import User  # registra FK dos modelos completos
import app.produto_identidade_models  # noqa: F401
import app.grupo_comercial_models  # noqa: F401
import app.especie_raca_mestre_models  # noqa: F401
import app.financeiro_models  # noqa: F401
import app.caixa_models  # noqa: F401
from app.produtos_models import Produto
from app.produto_identity_models import ProdutoSkuAlias
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.vendas_models import Venda, VendaItem, VendaPagamento
from app.financeiro_models import ContaReceber
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodEvent, IfoodOrder, IfoodPdvBridge
from app.integrations.ifood.pdv_pilot import (
    block_pilot_sale_edit,
    complete_pilot_cancellation,
    complete_pilot_finalization,
    import_pdv_pilot,
    is_pilot_external_delivery,
    pdv_bridge_summary,
    pilot_settings_reason,
    prepare_pilot_cancellation,
    prepare_pilot_finalization,
    validate_pilot_payload,
)
from app.estoque_reserva_service import EstoqueReservaService


def virtual_bag(order_id, merchant_id):
    return {
        "id": order_id,
        "shortCode": "DEV01",
        "test": True,
        "merchant": {"id": merchant_id},
        "operationMode": {"type": "TAKEOUT"},
        "bag": {
            "items": [
                {
                    "uniqueId": "item-1",
                    "name": "Produto de teste",
                    "ean": "7898401961203",
                    "quantity": 1,
                    "product": {"isVariableWeight": False},
                    "unavailable": False,
                    "prices": {"unitValue": {"value": 6500}},
                }
            ],
            "prices": {"grossValue": {"value": 6500}},
        },
        "payment": {
            "methods": [{"name": "Cash", "inPerson": True, "amount": {"value": 6500}}]
        },
    }


def configure(monkeypatch, tenant_id, merchant_id, order_id):
    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "ENVIRONMENT": "test",
        "IFOOD_PDV_PILOT_ENABLED": True,
        "IFOOD_PDV_PILOT_TENANT_ID": str(tenant_id),
        "IFOOD_PDV_PILOT_MERCHANT_ID": str(merchant_id),
        "IFOOD_PDV_PILOT_ORDER_ID": str(order_id),
        "IFOOD_PDV_PILOT_SKU": "018631.1",
    }.items():
        monkeypatch.setattr(settings, key, value)


@pytest.fixture
def source_order(monkeypatch):
    tenant_id, merchant_id, order_id = uuid4(), str(uuid4()), str(uuid4())
    configure(monkeypatch, tenant_id, merchant_id, order_id)
    return SimpleNamespace(
        tenant_id=tenant_id,
        merchant_id=merchant_id,
        ifood_order_id=order_id,
        status="PLACED",
        payload=virtual_bag(order_id, merchant_id),
    )


def test_virtual_bag_uses_cents_and_in_person_payment(source_order):
    result = validate_pilot_payload(source_order)
    assert result["price"] == Decimal("65")
    assert result["quantity"] == 1
    assert result["ean"] == "7898401961203"


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(test=False),
        lambda p: p.update(test="true"),
        lambda p: p["merchant"].update(id=str(uuid4())),
        lambda p: p["operationMode"].update(type="DELIVERY"),
        lambda p: p["bag"]["items"].append(deepcopy(p["bag"]["items"][0])),
        lambda p: p["bag"]["items"][0].update(quantity=2),
        lambda p: p["bag"]["items"][0].update(quantity="NaN"),
        lambda p: p["bag"]["items"][0].update(unavailable=True),
        lambda p: p["bag"]["items"][0].update(ean=""),
        lambda p: p["bag"]["prices"]["grossValue"].update(value=6400),
        lambda p: p.update(benefits=[{"value": 1}]),
        lambda p: p["payment"]["methods"][0].update(inPerson=False),
        lambda p: p["payment"]["methods"][0].pop("inPerson"),
        lambda p: p["payment"]["methods"][0]["amount"].update(value=6600),
        lambda p: p["payment"]["methods"][0]["amount"].update(currency="USD"),
        lambda p: p["bag"]["items"][0]["product"].update(isVariableWeight=True),
        lambda p: p["bag"]["items"][0].pop("uniqueId"),
        lambda p: p.update(merchant=[]),
        lambda p: p.update(operationMode=[]),
        lambda p: p.update(bag=[]),
        lambda p: p["bag"].update(prices=[]),
        lambda p: p["bag"]["items"][0].update(prices=[]),
        lambda p: p["bag"]["items"][0].update(product=[]),
        lambda p: p.update(payment=[]),
    ],
)
def test_unapproved_order_is_rejected_before_database(source_order, change):
    change(source_order.payload)
    with pytest.raises(HTTPException) as exc:
        validate_pilot_payload(source_order)
    assert exc.value.status_code == 409


@pytest.mark.parametrize("state", ["CONCLUDED", "CANCELLED", "DISPATCHED", "UNKNOWN"])
def test_terminal_order_cannot_create_retroactive_reservation(source_order, state):
    source_order.status = state
    with pytest.raises(HTTPException):
        validate_pilot_payload(source_order)


@pytest.mark.parametrize("key", ["ENVIRONMENT", "APP_ENV", "ENV"])
def test_production_cannot_be_enabled_even_with_pilot_flag(
    source_order, monkeypatch, key
):
    monkeypatch.setenv(key, "production")
    assert "exclusivo" in pilot_settings_reason()


def test_missing_scope_and_different_order_tenant_merchant_are_blocked(
    source_order, monkeypatch
):
    assert pilot_settings_reason(tenant_id=uuid4())
    assert pilot_settings_reason(merchant_id=str(uuid4()))
    assert pilot_settings_reason(order_id=str(uuid4()))
    monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_ORDER_ID", "")
    assert pilot_settings_reason()
    # Polling da loja de teste pode mantê-la conectada antes de gerar o pedido.
    assert pilot_settings_reason(require_order=False) is None


@pytest.fixture
def pilot_db(monkeypatch, tenant_context):
    engine = create_engine("sqlite://")
    # Contrato ORM real em DB isolado; chaves cruzadas/RLS sao testadas no PG.
    for model in (
        User,
        Produto,
        ProdutoSkuAlias,
        PedidoIntegrado,
        PedidoIntegradoItem,
        Venda,
        VendaItem,
        VendaPagamento,
        ContaReceber,
        IfoodMerchantConfig,
        IfoodOrder,
        IfoodEvent,
        IfoodPdvBridge,
    ):
        with engine.begin() as conn:
            conn.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    db_session = Session(engine, expire_on_commit=False)
    tenant = SimpleNamespace(id=uuid4())
    tenant_context(tenant.id)
    user = User(
        tenant_id=tenant.id,
        nome="Operador DEV",
        email=f"{uuid4().hex}@test.invalid",
        hashed_password="not-a-login-secret",
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    merchant_id, order_id = str(uuid4()), str(uuid4())
    configure(monkeypatch, tenant.id, merchant_id, order_id)
    product = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo="018631.1",
        nome="Produto teste",
        codigo_barras="7898401961203",
        gtin_ean="7898401961203",
        unidade="UN",
        tipo_produto="SIMPLES",
        ativo=True,
        estoque_atual=31,
        preco_venda=65,
        preco_custo=43,
    )
    control = Produto(
        tenant_id=tenant.id,
        user_id=user.id,
        codigo="OUTRO",
        nome="Controle",
        unidade="UN",
        tipo_produto="SIMPLES",
        ativo=True,
        estoque_atual=19,
    )
    config = IfoodMerchantConfig(
        tenant_id=tenant.id, merchant_id=merchant_id, active=True
    )
    order = IfoodOrder(
        tenant_id=tenant.id,
        merchant_id=merchant_id,
        ifood_order_id=order_id,
        status="PLACED",
        payload=virtual_bag(order_id, merchant_id),
    )
    previous = PedidoIntegrado(
        tenant_id=tenant.id,
        pedido_bling_id="previous-order",
        canal="teste",
        status="aberto",
        expira_em=PedidoIntegrado.calcular_expiracao(),
        payload={},
    )
    db_session.add_all([product, control, config, order, previous])
    db_session.flush()
    db_session.add(
        PedidoIntegradoItem(
            tenant_id=tenant.id,
            pedido_integrado_id=previous.id,
            sku="018631.1",
            quantidade=3,
        )
    )
    db_session.flush()
    try:
        yield SimpleNamespace(
            db=db_session,
            tenant_id=tenant.id,
            user_id=user.id,
            order=order,
            product=product,
            control=control,
        )
    finally:
        db_session.rollback()
        db_session.close()
        engine.dispose()


def test_import_is_reserved_once_without_physical_decrease_or_bling_id(pilot_db):
    c = pilot_db
    assert pdv_bridge_summary(c.db, c.order)["eligible"] is True
    for _ in range(2):
        import_pdv_pilot(
            c.db,
            tenant_id=c.tenant_id,
            order_id=c.order.ifood_order_id,
            actor_id=c.user_id,
        )
        c.db.flush()
    assert c.db.query(IfoodPdvBridge).count() == 1
    bridge = c.db.query(IfoodPdvBridge).one()
    sale = c.db.query(Venda).one()
    assert sale.canal == "ifood" and sale.status == "aberta"
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19
    assert (
        EstoqueReservaService.quantidade_reservada_produto(c.db, c.tenant_id, c.product)
        == 4
    )
    reservation = c.db.query(PedidoIntegrado).filter_by(id=bridge.reservation_id).one()
    assert reservation.pedido_bling_id is None and reservation.canal == "ifood"
    assert pdv_bridge_summary(c.db, c.order)["sale_id"] == sale.id


def test_cancel_unconsumed_reservation_never_replenishes_stock(pilot_db):
    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    bridge = prepare_pilot_cancellation(c.db, sale)
    assert bridge.stock_decreased_at is None
    complete_pilot_cancellation(c.db, bridge)
    c.db.flush()
    assert (
        EstoqueReservaService.quantidade_reservada_produto(c.db, c.tenant_id, c.product)
        == 3
    )
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19
    assert bridge.status == "cancelled"
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"valor": 65, "forma_pagamento": "Dinheiro"}]
        )


def test_finalization_marker_and_reservation_are_same_transaction(pilot_db):
    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    bridge = prepare_pilot_finalization(
        c.db, sale, [{"valor": 65, "forma_pagamento": "Dinheiro"}]
    )
    complete_pilot_finalization(c.db, bridge)
    c.db.flush()
    assert bridge.status == "sold" and bridge.stock_decreased_at
    assert (
        EstoqueReservaService.quantidade_reservada_produto(c.db, c.tenant_id, c.product)
        == 3
    )
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"valor": 65, "forma_pagamento": "Dinheiro"}]
        )


def test_editing_sale_or_changed_origin_is_blocked(pilot_db):
    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    with pytest.raises(HTTPException):
        block_pilot_sale_edit(c.db, sale)
    sale.itens[0].quantidade = 2
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"valor": 65, "forma_pagamento": "Dinheiro"}]
        )
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19


@pytest.mark.parametrize(
    "field,value",
    [("merchant", []), ("payment", []), ("bag", []), ("operationMode", [])],
)
def test_malformed_shapes_return_blocked_summary_without_mutation(
    pilot_db, field, value
):
    c = pilot_db
    c.order.payload = {**c.order.payload, field: value}
    assert pdv_bridge_summary(c.db, c.order)["eligible"] is False
    assert pdv_bridge_summary(c.db, c.order)["status"] == "blocked"
    assert c.db.query(Venda).count() == c.db.query(IfoodPdvBridge).count() == 0
    assert (
        EstoqueReservaService.quantidade_reservada_produto(c.db, c.tenant_id, c.product)
        == 3
    )


def test_changed_unique_item_cannot_finalize_previous_reservation(pilot_db):
    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    payload = deepcopy(c.order.payload)
    payload["bag"]["items"][0]["uniqueId"] = "different-item"
    c.order.payload = payload
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db,
            c.db.query(Venda).one(),
            [{"valor": 65, "forma_pagamento": "Dinheiro"}],
        )
    assert c.product.estoque_atual == 31


def test_different_ean_and_uncovered_stock_do_not_create_partial_sale(pilot_db):
    c = pilot_db
    payload = deepcopy(c.order.payload)
    payload["bag"]["items"][0]["ean"] = "7898401961204"
    c.order.payload = payload
    with pytest.raises(HTTPException):
        import_pdv_pilot(
            c.db,
            tenant_id=c.tenant_id,
            order_id=c.order.ifood_order_id,
            actor_id=c.user_id,
        )
    assert c.db.query(Venda).count() == c.db.query(IfoodPdvBridge).count() == 0
    c.order.payload = virtual_bag(c.order.ifood_order_id, c.order.merchant_id)
    c.product.estoque_atual = 3
    with pytest.raises(HTTPException):
        import_pdv_pilot(
            c.db,
            tenant_id=c.tenant_id,
            order_id=c.order.ifood_order_id,
            actor_id=c.user_id,
        )
    assert c.db.query(Venda).count() == c.db.query(IfoodPdvBridge).count() == 0
    assert c.control.estoque_atual == 19


def test_cash_order_cannot_be_finalized_with_different_payment(pilot_db):
    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, c.db.query(Venda).one(), [{"valor": 65, "forma_pagamento": "PIX"}]
        )
    assert c.db.query(IfoodPdvBridge).one().status == "reserved"


def test_old_events_and_terminal_states_do_not_reopen_order(pilot_db):
    from app.integrations.ifood.orders import upsert_ifood_order

    c = pilot_db
    c.order.status = "CONCLUDED"
    c.order.last_event_at = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
    original_payload = deepcopy(c.order.payload)
    upsert_ifood_order(
        c.db,
        tenant_id=c.tenant_id,
        merchant_id=c.order.merchant_id,
        order_id=c.order.ifood_order_id,
        payload={"id": c.order.ifood_order_id, "status": "PLACED"},
        event_status="PLACED",
        event_at=datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc),
    )
    c.db.flush()
    assert c.order.status == "CONCLUDED"
    assert c.order.payload == original_payload
    upsert_ifood_order(
        c.db,
        tenant_id=c.tenant_id,
        merchant_id=c.order.merchant_id,
        order_id=c.order.ifood_order_id,
        payload={},
        event_status="CONFIRMED",
        event_at=datetime(2026, 10, 24, 11, 0, tzinfo=timezone.utc),
    )
    assert c.order.status == "CONCLUDED"
    assert pdv_bridge_summary(c.db, c.order)["eligible"] is False


def test_upsert_refreshes_cached_order_before_comparing_terminal_state(pilot_db):
    """Outro processador pode ter confirmado CAN apos esta sessao ler PLACED."""
    from app.integrations.ifood.orders import upsert_ifood_order

    c = pilot_db
    c.db.commit()
    cached = c.order
    assert cached.status == "PLACED"
    with Session(c.db.get_bind()) as concurrent:
        actual = (
            concurrent.query(IfoodOrder)
            .filter(IfoodOrder.ifood_order_id == c.order.ifood_order_id)
            .one()
        )
        actual.status = "CANCELLED"
        actual.last_event_at = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        concurrent.commit()
    assert cached.status == "PLACED"
    upsert_ifood_order(
        c.db,
        tenant_id=c.tenant_id,
        merchant_id=c.order.merchant_id,
        order_id=c.order.ifood_order_id,
        payload={},
        event_status="CONFIRMED",
        event_at=datetime(2026, 10, 24, 11, 0, tzinfo=timezone.utc),
    )
    c.db.flush()
    assert cached.status == "CANCELLED"
    assert c.db.query(IfoodPdvBridge).count() == c.db.query(Venda).count() == 0


def test_polling_does_not_ack_or_store_events_from_another_merchant(pilot_db):
    from app.integrations.ifood.orders import process_order_events

    c = pilot_db
    acknowledgments = []
    client = SimpleNamespace(
        poll_events=lambda merchants: [
            {
                "id": "wrong-merchant-event",
                "orderId": c.order.ifood_order_id,
                "merchantId": str(uuid4()),
                "code": "PLC",
            }
        ],
        acknowledge_events=lambda ids: acknowledgments.append(ids),
    )
    config = c.db.query(IfoodMerchantConfig).one()
    result = process_order_events(
        c.db, tenant_id=c.tenant_id, config=config, client=client
    )
    assert result["failed"] == 1 and result["acknowledged"] == 0
    assert acknowledgments == [] and c.db.query(IfoodEvent).count() == 0
    assert c.db.query(IfoodPdvBridge).count() == c.db.query(Venda).count() == 0


def test_polling_rejects_unapproved_company_before_calling_provider(pilot_db):
    from app.integrations.ifood.client import IfoodClientError
    from app.integrations.ifood.orders import process_order_events

    c = pilot_db
    called = []
    client = SimpleNamespace(poll_events=lambda merchants: called.append(merchants))
    with pytest.raises(IfoodClientError):
        process_order_events(
            c.db,
            tenant_id=uuid4(),
            config=c.db.query(IfoodMerchantConfig).one(),
            client=client,
        )
    assert called == []


def delivery_without_charges(payload):
    payload = deepcopy(payload)
    payload["operationMode"] = {
        "type": "DELIVERY",
        "delivery": {
            "provider": "IFOOD",
            "prices": {"grossValue": {"value": 0, "currency": "BRL"}},
        },
    }
    return payload


def delivery_with_freight(payload, cents=890):
    payload = delivery_without_charges(payload)
    payload["operationMode"]["delivery"]["prices"] = {
        "grossValue": {"value": cents, "currency": "BRL"},
        "discount": {"value": 0, "currency": "BRL"},
        "netValue": {"value": cents, "currency": "BRL"},
    }
    payload["payment"]["methods"][0]["amount"]["value"] = 6500 + cents
    return payload


def test_takeout_official_hyphen_alias_has_same_evidence(source_order):
    original = validate_pilot_payload(source_order)
    source_order.payload["operationMode"]["type"] = "TAKE-OUT"
    alias = validate_pilot_payload(source_order)
    assert alias["operation_type"] == "TAKEOUT"
    assert alias["evidence_hash"] == original["evidence_hash"]


def test_delivery_accepts_explicit_free_shipping_and_no_fees(source_order):
    source_order.payload = delivery_without_charges(source_order.payload)
    assert validate_pilot_payload(source_order)["operation_type"] == "DELIVERY"
    assert validate_pilot_payload(source_order)["price"] == Decimal(65)
    source_order.payload["fees"] = [
        {
            "audience": "CUSTOMER",
            "prices": {
                key: {"value": 0, "currency": "BRL"}
                for key in ("grossValue", "discount", "netValue")
            },
        }
    ]
    assert validate_pilot_payload(source_order)["price"] == Decimal(65)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            value=1
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            currency="USD"
        ),
        lambda p: p["operationMode"]["delivery"].pop("prices"),
        lambda p: p["operationMode"]["delivery"]["prices"].update(
            discount={"value": 50}
        ),
        lambda p: p["operationMode"]["delivery"]["prices"].update(
            netValue={"value": 50}
        ),
        lambda p: p.update(
            fees=[
                {
                    "prices": {
                        "grossValue": {"value": 100},
                        "discount": {"value": 0},
                        "netValue": {"value": 100},
                    }
                }
            ]
        ),
        lambda p: p.update(fees=[{"prices": {"grossValue": {"value": 0}}}]),
        lambda p: p.update(fees={}),
        lambda p: p.update(benefit={"benefits": [{"value": 100}]}),
        lambda p: p.update(benefit=[]),
    ],
)
def test_delivery_inconsistent_unknown_cost_or_nested_benefit_is_rejected(
    source_order, change
):
    source_order.payload = delivery_without_charges(source_order.payload)
    change(source_order.payload)
    with pytest.raises(HTTPException) as exc:
        validate_pilot_payload(source_order)
    assert exc.value.status_code == 409


def test_delivery_preserves_merchandise_freight_and_full_cash_total(source_order):
    source_order.payload = delivery_with_freight(source_order.payload)
    result = validate_pilot_payload(source_order)
    assert result["price"] == Decimal("65")
    assert result["shipping_price"] == Decimal("8.90")
    assert result["total"] == Decimal("73.90")
    assert result["quantity"] == 1
    assert result["operation_type"] == "DELIVERY"


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            value=-890
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            value=890.1
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            value=True
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            value="NaN"
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            value=9999999999
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["grossValue"].update(
            currency="USD"
        ),
        lambda p: p["operationMode"]["delivery"]["prices"]["discount"].update(value=1),
        lambda p: p["operationMode"]["delivery"]["prices"]["netValue"].update(
            value=889
        ),
        lambda p: p["payment"]["methods"][0]["amount"].update(value=6500),
        lambda p: p["payment"]["methods"][0]["amount"].update(value=7390.1),
        lambda p: p["bag"]["prices"]["grossValue"].update(value=7390),
    ],
)
def test_delivery_freight_must_reconcile_without_guessing_costs(source_order, change):
    source_order.payload = delivery_with_freight(source_order.payload)
    change(source_order.payload)
    with pytest.raises(HTTPException) as exc:
        validate_pilot_payload(source_order)
    assert exc.value.status_code == 409


def test_delivery_cash_total_reserves_only_item_and_is_displayed_in_panel(pilot_db):
    from app.integrations.ifood.orders import order_detail, upsert_ifood_order

    c = pilot_db
    order = upsert_ifood_order(
        c.db,
        tenant_id=c.tenant_id,
        merchant_id=c.order.merchant_id,
        order_id=c.order.ifood_order_id,
        payload=delivery_with_freight(c.order.payload),
        event_status="PLACED",
    )
    assert order_detail(order)["total"] == 73.90
    for _ in range(2):
        import_pdv_pilot(
            c.db,
            tenant_id=c.tenant_id,
            order_id=order.ifood_order_id,
            actor_id=c.user_id,
        )
    sale = c.db.query(Venda).one()
    bridge = c.db.query(IfoodPdvBridge).one()
    assert sale.subtotal == bridge.unit_price == Decimal("65")
    assert sale.taxa_entrega == Decimal("8.90")
    assert sale.total == Decimal("73.90")
    assert sale.tem_entrega is True and sale.tipo_retirada is None
    assert sale.entregador_id is None and sale.cliente_id is None
    assert sale.itens[0].quantidade == bridge.quantity == 1
    assert (
        EstoqueReservaService.quantidade_reservada_produto(c.db, c.tenant_id, c.product)
        == 4
    )
    assert is_pilot_external_delivery(c.db, sale) is True
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": 65}]
        )
    assert (
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": Decimal("73.90")}]
        )
        is bridge
    )
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19


@pytest.mark.parametrize("state", ["CONCLUDED", "CANCELLED"])
def test_delivery_terminal_refresh_keeps_full_display_total_without_new_reserve(
    pilot_db, state
):
    from app.integrations.ifood.orders import upsert_ifood_order

    c = pilot_db
    order = upsert_ifood_order(
        c.db,
        tenant_id=c.tenant_id,
        merchant_id=c.order.merchant_id,
        order_id=c.order.ifood_order_id,
        payload=delivery_with_freight(c.order.payload),
        event_status=state,
    )
    assert order.total == 73.90 and order.status == state
    with pytest.raises(HTTPException):
        import_pdv_pilot(
            c.db,
            tenant_id=c.tenant_id,
            order_id=order.ifood_order_id,
            actor_id=c.user_id,
        )
    assert c.db.query(IfoodPdvBridge).count() == c.db.query(Venda).count() == 0
    assert c.product.estoque_atual == 31


@pytest.mark.parametrize("allowed", ["disabled", "other_tenant"])
def test_delivery_total_override_never_changes_nonpilot_legacy_reading(
    pilot_db, monkeypatch, allowed
):
    from app.integrations.ifood.orders import upsert_ifood_order

    c = pilot_db
    if allowed == "disabled":
        monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_ENABLED", False)
    else:
        monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_TENANT_ID", str(uuid4()))
    order = upsert_ifood_order(
        c.db,
        tenant_id=c.tenant_id,
        merchant_id=c.order.merchant_id,
        order_id=c.order.ifood_order_id,
        payload=delivery_with_freight(c.order.payload),
        event_status="PLACED",
    )
    assert order.total == 65
    assert c.db.query(IfoodPdvBridge).count() == c.db.query(Venda).count() == 0


@pytest.mark.parametrize(
    "field,value", [("subtotal", 64), ("taxa_entrega", 0), ("total", 65)]
)
def test_delivery_cannot_finalize_after_local_total_or_freight_edit(
    pilot_db, field, value
):
    c = pilot_db
    c.order.payload = delivery_with_freight(c.order.payload)
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    setattr(sale, field, value)
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": Decimal("73.90")}]
        )
    assert c.db.query(IfoodPdvBridge).one().status == "reserved"
    assert c.product.estoque_atual == 31


def test_changed_provider_freight_and_cash_total_invalidate_reserved_snapshot(pilot_db):
    c = pilot_db
    c.order.payload = delivery_with_freight(c.order.payload)
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    bridge = c.db.query(IfoodPdvBridge).one()
    c.order.payload = delivery_with_freight(c.order.payload, cents=990)
    assert validate_pilot_payload(c.order)["evidence_hash"] != bridge.evidence_hash
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": Decimal("74.90")}]
        )
    assert sale.taxa_entrega == Decimal("8.90") and sale.total == Decimal("73.90")
    assert bridge.status == "reserved" and c.product.estoque_atual == 31


def test_delivery_keeps_true_mode_without_creating_local_driver_or_shipping_charge(
    pilot_db,
):
    c = pilot_db
    c.order.payload = delivery_without_charges(c.order.payload)
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    assert sale.tem_entrega is True and sale.tipo_retirada is None
    assert sale.entregador_id is None and sale.taxa_entrega == 0
    assert sale.total == Decimal(65)
    assert is_pilot_external_delivery(c.db, sale) is True
    assert (
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": 65}]
        ).status
        == "reserved"
    )
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19


def test_delivery_exemption_does_not_allow_other_origins_or_changed_freight(pilot_db):
    c = pilot_db
    assert is_pilot_external_delivery(c.db, SimpleNamespace(canal="app")) is False
    c.order.payload = delivery_without_charges(c.order.payload)
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    sale = c.db.query(Venda).one()
    payload = deepcopy(c.order.payload)
    payload["operationMode"]["delivery"]["prices"]["grossValue"]["value"] = 100
    c.order.payload = payload
    with pytest.raises(HTTPException):
        is_pilot_external_delivery(c.db, sale)
    assert c.product.estoque_atual == 31


def emit_bag_change(c, code, full_code):
    from app.integrations.ifood.orders import process_order_events

    event = {
        "id": str(uuid4()),
        "orderId": c.order.ifood_order_id,
        "merchantId": c.order.merchant_id,
        "code": code,
        "fullCode": full_code,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    client = SimpleNamespace(
        poll_events=lambda merchants: [event],
        acknowledge_events=lambda ids: {"status_code": 202},
    )
    return process_order_events(
        c.db,
        tenant_id=c.tenant_id,
        config=c.db.query(IfoodMerchantConfig).one(),
        client=client,
    )


@pytest.mark.parametrize(
    "code,full_code",
    [("OPA", "ORDER_PATCHED"), ("SPE", "SEPARATION_ENDED"), ("OPA", None)],
)
def test_bag_change_event_blocks_old_hash_until_fresh_unchanged_virtual_bag(
    pilot_db, code, full_code
):
    from app.routes.ifood_order_routes import _refresh_virtual_bag

    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    c.db.commit()
    assert emit_bag_change(c, code, full_code)["acknowledged"] == 1
    sale = c.db.query(Venda).one()
    assert "Consulte novamente" in pdv_bridge_summary(c.db, c.order)["reason"]
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": 65}]
        )
    assert c.product.estoque_atual == 31
    client = SimpleNamespace(get_virtual_bag=lambda order_id: deepcopy(c.order.payload))
    details = _refresh_virtual_bag(
        db=c.db, tenant_id=c.tenant_id, order=c.order, client=client
    )
    assert c.order.last_action == "pdv_bag_reviewed"
    assert details["pdv_bridge"]["status"] == "reserved"
    assert (
        prepare_pilot_finalization(
            c.db, sale, [{"forma_pagamento": "Dinheiro", "valor": 65}]
        ).status
        == "reserved"
    )
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19


def test_fresh_bag_with_changed_item_stays_blocked_and_never_recalculates_reservation(
    pilot_db,
):
    from app.integrations.ifood.orders import mark_order_action
    from app.routes.ifood_order_routes import _refresh_virtual_bag

    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    c.db.commit()
    emit_bag_change(c, "OPA", "ORDER_PATCHED")
    changed = deepcopy(c.order.payload)
    changed["bag"]["items"][0]["uniqueId"] = "substituted-item"
    _refresh_virtual_bag(
        db=c.db,
        tenant_id=c.tenant_id,
        order=c.order,
        client=SimpleNamespace(get_virtual_bag=lambda oid: changed),
    )
    assert c.order.last_action == "pdv_bag_review_required"
    mark_order_action(c.order, "confirm")
    assert c.order.last_action == "pdv_bag_review_required"
    assert c.order.payload["bag"]["items"][0]["uniqueId"] == "substituted-item"
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db,
            c.db.query(Venda).one(),
            [{"forma_pagamento": "Dinheiro", "valor": 65}],
        )
    assert c.db.query(IfoodPdvBridge).count() == c.db.query(Venda).count() == 1
    assert (
        EstoqueReservaService.quantidade_reservada_produto(c.db, c.tenant_id, c.product)
        == 4
    )
    assert c.product.estoque_atual == 31 and c.control.estoque_atual == 19


def test_pending_bag_change_event_cannot_be_approved_before_processing(pilot_db):
    from app.integrations.ifood.pdv_pilot import pilot_bag_review_reason

    c = pilot_db
    import_pdv_pilot(
        c.db, tenant_id=c.tenant_id, order_id=c.order.ifood_order_id, actor_id=c.user_id
    )
    c.order.last_action = "pdv_bag_reviewed"
    c.order.last_action_at = datetime.now(timezone.utc)
    c.db.add(
        IfoodEvent(
            tenant_id=c.tenant_id,
            merchant_id=c.order.merchant_id,
            ifood_order_id=c.order.ifood_order_id,
            ifood_event_id=str(uuid4()),
            code="OPA",
            full_code="ORDER_PATCHED",
            payload={},
            processed_at=None,
        )
    )
    c.db.flush()
    assert pilot_bag_review_reason(c.db, c.order, c.db.query(IfoodPdvBridge).one())
    with pytest.raises(HTTPException):
        prepare_pilot_finalization(
            c.db,
            c.db.query(Venda).one(),
            [{"forma_pagamento": "Dinheiro", "valor": 65}],
        )


def test_cancellation_request_states_remain_visible_without_reopening_terminal_order(
    pilot_db,
):
    from app.integrations.ifood.orders import upsert_ifood_order

    c = pilot_db
    c.order.status = "CONFIRMED"
    for state in ("CANCELLATION_REQUESTED", "CANCELLATION_REQUEST_FAILED"):
        upsert_ifood_order(
            c.db,
            tenant_id=c.tenant_id,
            merchant_id=c.order.merchant_id,
            order_id=c.order.ifood_order_id,
            payload={},
            event_status=state,
            event_at=datetime.now(timezone.utc),
        )
        assert c.order.status == state
    c.order.status = "CANCELLED"
    for state in ("CANCELLATION_REQUESTED", "CANCELLATION_REQUEST_FAILED", "CONFIRMED"):
        upsert_ifood_order(
            c.db,
            tenant_id=c.tenant_id,
            merchant_id=c.order.merchant_id,
            order_id=c.order.ifood_order_id,
            payload={},
            event_status=state,
            event_at=datetime.now(timezone.utc),
        )
        assert c.order.status == "CANCELLED"
