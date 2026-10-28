"""Vinculos exatos, comprovantes originais e isolamento do CMV historico."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from decimal import Decimal
from pathlib import Path
import runpy
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app import caixa_models, financeiro_models, produtos_models  # noqa: F401 - relational registry
from app.models import Cliente  # noqa: F401 - relational registry
from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import (
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodFinancialSnapshot,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
from app.integrations.ifood.financial import (
    IfoodFinancialError,
    get_financial_order,
    get_financial_report,
    record_order_costs,
)
from app.integrations.ifood.financial_costs import (
    get_historical_costs_for_orders,
    get_order_historical_cost,
    link_order_sale,
    list_linkable_sales,
)
from app.tenancy.context import set_current_tenant, tenant_context
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaItem
from app.utils.timezone import BRASILIA_TZ
from app.vendas.custo_original import registrar_custo_original_saida

MERCHANT = "184bad64-04a8-4877-9789-2e246b3ae4e4"
ORDER = "003f1a11-63b5-45c6-a956-e6423f8a06ca"
NOW = datetime(2025, 3, 2, 12, tzinfo=timezone.utc)
TABLES = (
    IfoodMerchantConfig,
    IfoodFinancialSnapshot,
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodOrder,
    Venda,
    VendaItem,
    VendaDevolucao,
    IfoodFinancialSaleLink,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    for model in TABLES:
        model.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(
            CreateTable(IfoodPdvBridge.__table__, include_foreign_key_constraints=[])
        )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def store(db, *, merchant=MERCHANT):
    tenant = uuid4()
    set_current_tenant(tenant)
    db.execute(
        IfoodMerchantConfig.__table__.insert().values(
            tenant_id=tenant, merchant_id=merchant, active=False
        )
    )
    db.commit()
    return tenant


def financial_order(db, tenant, *, order=ORDER, merchant=MERCHANT):
    snapshot = IfoodFinancialSnapshot.__table__
    snapshot_id = db.execute(
        select(snapshot.c.id).where(
            snapshot.c.tenant_id == tenant, snapshot.c.merchant_id == merchant
        )
    ).scalar_one_or_none()
    if snapshot_id is None:
        snapshot_id = db.execute(
            snapshot.insert().values(
                tenant_id=tenant,
                merchant_id=merchant,
                mode="homologation",
                begin_date=NOW.date(),
                end_date=NOW.date(),
                revision=1,
                active=True,
                source="synthetic",
                payload_hash=uuid4().hex,
                page_count=1,
                event_count=1,
                actor_id=7,
            )
        ).inserted_primary_key[0]
    position = (
        db.execute(
            select(func.count())
            .select_from(IfoodFinancialEvent.__table__)
            .where(IfoodFinancialEvent.snapshot_id == snapshot_id)
        ).scalar_one()
        + 1
    )
    db.execute(
        IfoodFinancialEvent.__table__.insert().values(
            tenant_id=tenant,
            snapshot_id=snapshot_id,
            position=position,
            order_id=order,
            name="ORDER_PAYMENT",
            trigger="SALE_CONCLUDED",
            amount=100,
            has_transfer_impact=True,
            evidence={},
        )
    )
    return order


def sale(db, tenant, *, quantity="2", cost="60.00", **changes):
    values = dict(
        tenant_id=tenant,
        numero_venda="VEN-" + uuid4().hex[:10],
        vendedor_id=7,
        user_id=7,
        subtotal=100,
        total=100,
        canal="ifood",
        status="finalizada",
        data_venda=NOW,
        data_finalizacao=NOW,
        rentabilidade_snapshot={"cmv": "999.99"},
    )
    values.update(changes)
    sale_id = db.execute(
        Venda.__table__.insert().values(**values)
    ).inserted_primary_key[0]
    item_id = add_item(db, tenant, sale_id, quantity=quantity, cost=cost)
    return sale_id, item_id


def add_item(
    db,
    tenant,
    sale_id,
    *,
    quantity="2",
    cost="60.00",
    product_id=11,
    movement=None,
    stock_tenant=None,
):
    item_id = db.execute(
        VendaItem.__table__.insert().values(
            tenant_id=tenant,
            venda_id=sale_id,
            tipo="produto",
            produto_id=product_id,
            quantidade=Decimal(quantity),
            preco_unitario=50,
            subtotal=100,
            estoque_origem_tenant_id=stock_tenant,
        )
    ).inserted_primary_key[0]
    db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.id == item_id)
        .values(
            custo_original_saida={
                "versao": 1,
                "origem": "baixa_estoque_venda",
                "venda_id": sale_id,
                "venda_item_id": item_id,
                "produto_id": product_id,
                "tenant_estoque_id": str(stock_tenant or tenant),
                "movimentacao_id": movement or item_id + 500,
                "quantidade": quantity,
                "custo_total": cost,
                "capturado_em": NOW.isoformat(),
            }
        )
    )
    return item_id


def proof(db, item_id, **changes):
    table = VendaItem.__table__
    value = deepcopy(
        db.execute(
            select(table.c.custo_original_saida).where(table.c.id == item_id)
        ).scalar_one()
    )
    value.update(changes)
    db.execute(
        table.update().where(table.c.id == item_id).values(custo_original_saida=value)
    )


def link(db, tenant, sale_id, order=ORDER, **kwargs):
    with tenant_context(tenant):
        return link_order_sale(
            db,
            tenant,
            MERCHANT,
            order,
            sale_id,
            "Pedido confirmado pelo operador DEV",
            7,
            **kwargs,
        )


def cost(db, tenant, order=ORDER, **kwargs):
    with tenant_context(tenant):
        return get_order_historical_cost(db, tenant, MERCHANT, order, **kwargs)


def scenario(db, **changes):
    tenant = store(db)
    financial_order(db, tenant)
    sale_id, item_id = sale(db, tenant, **changes)
    return tenant, sale_id, item_id


def test_unlinked_exact_sale_does_not_match_by_amount_date_or_product(db):
    tenant, sale_id, _ = scenario(db)
    result = cost(db, tenant)
    assert result["status"] == "pending"
    assert result["cmv"] is None and result["sale"] is None
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialSaleLink.__table__)
        ).scalar_one()
        == 0
    )


def test_confirmed_link_automates_original_cost_without_altering_sources_or_manual(db):
    tenant, sale_id, item_id = scenario(db)
    before = db.execute(select(VendaItem.__table__.c.custo_original_saida)).scalar_one()
    manual = IfoodFinancialOrderCosts.__table__
    db.execute(
        manual.insert().values(
            tenant_id=tenant,
            merchant_id=MERCHANT,
            mode="homologation",
            order_id=ORDER,
            version=1,
            cmv=42,
            source_note="Manual separado",
            actor_id=7,
        )
    )
    result = link(db, tenant, sale_id)
    assert result["status"] == "verified" and result["cmv"] == "60.00"
    assert result["source"] == "erp_original_stock_out"
    assert result["link"]["source"] == "explicit_confirmation"
    assert result["link"]["actor_id"] == 7
    assert result["items"][0]["movement_id"] == item_id + 500
    assert result["items"][0]["quantity"] == "2.000"
    assert cost(db, tenant) == result
    assert db.execute(select(manual.c.cmv)).scalar_one() == Decimal("42")
    assert (
        db.execute(select(VendaItem.__table__.c.custo_original_saida)).scalar_one()
        == before
    )
    assert db.execute(select(Venda.__table__.c.status)).scalar_one() == "finalizada"
    # Flush-only: caller pode reverter integralmente a confirmacao.
    db.rollback()
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialSaleLink.__table__)
        ).scalar_one()
        == 0
    )


def test_identical_products_have_independent_original_costs_and_unique_movements(db):
    tenant, sale_id, _ = scenario(db)
    add_item(db, tenant, sale_id, cost="5.01")
    result = link(db, tenant, sale_id)
    assert result["cmv"] == "65.01" and len(result["items"]) == 2


def test_same_stock_movement_cannot_prove_two_items(db):
    tenant, sale_id, item_id = scenario(db)
    add_item(db, tenant, sale_id, movement=item_id + 500)
    with pytest.raises(IfoodFinancialError, match="repetida"):
        link(db, tenant, sale_id)


@pytest.mark.parametrize(
    "changes",
    [
        {"venda_id": 999},
        {"venda_item_id": 999},
        {"produto_id": 999},
        {"quantidade": "1"},
        {"custo_total": "NaN"},
        {"custo_total": "Infinity"},
        {"custo_total": "0"},
        {"custo_total": "-1"},
        {"custo_total": "1.001"},
        {"custo_total": True},
        {"movimentacao_id": 0},
        {"movimentacao_id": True},
        {"versao": 2},
        {"versao": True},
        {"origem": "reprocessamento"},
        {"tenant_estoque_id": str(uuid4())},
        {"capturado_em": None},
        {"capturado_em": "2025-03-01"},
        {"capturado_em": "2025-02-30T10:00:00"},
        {"capturado_em": "2025-03-01T10:00:00+99:99"},
        {"capturado_em": "not-a-date"},
    ],
)
def test_invalid_original_proof_never_falls_back_to_reprocessed_or_current_cost(
    db, changes
):
    tenant, sale_id, item_id = scenario(db)
    proof(db, item_id, **changes)
    with pytest.raises(IfoodFinancialError, match="comprovado"):
        link(db, tenant, sale_id)
    assert cost(db, tenant)["cmv"] is None


@pytest.mark.parametrize(
    "column,value",
    [
        ("custo_original_saida", None),
        ("quantidade", 0),
        ("quantidade", -1),
        ("quantidade", Decimal("1.5")),
        ("tipo", "servico"),
        ("produto_id", None),
    ],
)
def test_incomplete_or_incompatible_item_blocks_initial_link(db, column, value):
    tenant, sale_id, item_id = scenario(db)
    db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.id == item_id)
        .values(**{column: value})
    )
    with pytest.raises(IfoodFinancialError):
        link(db, tenant, sale_id)


def test_shared_stock_proof_is_read_from_item_snapshot_without_cross_company_lookup(db):
    tenant = store(db)
    financial_order(db, tenant)
    sale_id, item_id = sale(db, tenant)
    stock_tenant = uuid4()
    db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.id == item_id)
        .values(estoque_origem_tenant_id=stock_tenant)
    )
    proof(db, item_id, tenant_estoque_id=str(stock_tenant))
    assert link(db, tenant, sale_id)["cmv"] == "60.00"


@pytest.mark.parametrize(
    "changes",
    [
        {"canal": "loja_fisica"},
        {"status": "aberta"},
        {"status": "cancelada"},
        {"data_cancelamento": NOW},
        {"cancelada_por": 7},
    ],
)
def test_only_finalized_ifood_sale_without_cancellation_can_link(db, changes):
    tenant, sale_id, _ = scenario(db, **changes)
    with pytest.raises(IfoodFinancialError):
        link(db, tenant, sale_id)


@pytest.mark.parametrize("change", ["delete", "add", "quantity", "proof"])
def test_manifest_detects_incomplete_or_changed_collection_after_confirmation(
    db, change
):
    tenant, sale_id, item_id = scenario(db)
    link(db, tenant, sale_id)
    if change == "delete":
        db.execute(VendaItem.__table__.delete().where(VendaItem.id == item_id))
    elif change == "add":
        add_item(db, tenant, sale_id, cost="3")
    elif change == "quantity":
        db.execute(
            VendaItem.__table__.update()
            .where(VendaItem.id == item_id)
            .values(quantidade=3)
        )
    else:
        proof(db, item_id, custo_total="99.00")
    result = cost(db, tenant)
    assert result["status"] == "pending" and result["cmv"] is None
    assert any("mudou" in missing for missing in result["missing"])


def add_return(db, tenant, sale_id):
    db.execute(
        VendaDevolucao.__table__.insert().values(
            tenant_id=tenant,
            venda_id=sale_id,
            chave_operacao=uuid4().hex,
            requisicao_hash=uuid4().hex,
            resposta={},
            user_id=7,
            data_competencia=NOW.date(),
            canal="ifood",
            status_original_venda="finalizada",
            forma_estorno="origem",
            motivo="Devolucao ficticia",
            valor_devolvido=1,
            custo_produtos_estornado=1,
            custo_servicos_estornado=0,
            custo_pendente=False,
            itens=[],
        )
    )


def test_returns_block_instead_of_inventing_net_original_cost(db):
    tenant, sale_id, _ = scenario(db)
    link(db, tenant, sale_id)
    add_return(db, tenant, sale_id)
    result = cost(db, tenant)
    assert result["cmv"] is None and result["items"][0]["cost"] == "60.00"
    assert any("devolução" in missing for missing in result["missing"])


def test_return_existing_before_link_is_rejected(db):
    tenant, sale_id, _ = scenario(db)
    add_return(db, tenant, sale_id)
    with pytest.raises(IfoodFinancialError, match="devolução"):
        link(db, tenant, sale_id)


@pytest.mark.parametrize("status", ["CANCELLED", "CANCELLATION_REQUESTED"])
def test_operational_cancellation_invalidates_linked_cost(db, status):
    tenant, sale_id, _ = scenario(db)
    link(db, tenant, sale_id)
    db.execute(
        IfoodOrder.__table__.insert().values(
            tenant_id=tenant,
            merchant_id=MERCHANT,
            ifood_order_id=ORDER,
            status=status,
            payload={},
        )
    )
    assert cost(db, tenant)["cmv"] is None


def test_exact_link_is_idempotent_but_never_reassigned(db):
    tenant, sale_id, _ = scenario(db)
    first = link(db, tenant, sale_id)
    assert link(db, tenant, sale_id)["link"]["id"] == first["link"]["id"]
    another_sale, _ = sale(db, tenant)
    with pytest.raises(IfoodFinancialError) as error:
        link(db, tenant, another_sale)
    assert error.value.status_code == 409
    financial_order(db, tenant, order="second-order")
    with pytest.raises(IfoodFinancialError):
        link(db, tenant, sale_id, order="second-order")


def test_tenant_and_merchant_scopes_do_not_leak_or_cross_link(db):
    tenant_a, sale_a, _ = scenario(db)
    link(db, tenant_a, sale_a)
    tenant_b = store(db)
    financial_order(db, tenant_b)
    assert cost(db, tenant_b)["sale"] is None
    with pytest.raises(IfoodFinancialError) as error:
        link(db, tenant_b, sale_a)
    assert error.value.status_code == 404
    with tenant_context(tenant_b), pytest.raises(IfoodFinancialError) as error:
        get_order_historical_cost(db, tenant_a, MERCHANT, ORDER)
    assert error.value.status_code == 403
    other_merchant = str(uuid4())
    db.execute(
        IfoodMerchantConfig.__table__.update()
        .where(IfoodMerchantConfig.tenant_id == tenant_a)
        .values(merchant_id=other_merchant)
    )
    with tenant_context(tenant_a):
        assert (
            get_order_historical_cost(db, tenant_a, other_merchant, ORDER)["sale"]
            is None
        )


def test_financial_order_must_exist_in_active_snapshot_for_same_merchant(db):
    tenant, sale_id, _ = scenario(db)
    db.execute(IfoodFinancialSnapshot.__table__.update().values(active=False))
    with pytest.raises(IfoodFinancialError) as error:
        link(db, tenant, sale_id)
    assert error.value.status_code == 404


def test_batch_is_bounded_queries_read_only_and_has_no_cost_product_lookup(db):
    tenant, sale_id, _ = scenario(db)
    link(db, tenant, sale_id)
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        with tenant_context(tenant):
            result = get_historical_costs_for_orders(
                db, tenant, MERCHANT, [ORDER] + [f"order-{i}" for i in range(300)]
            )
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert len(result) == 301 and result[ORDER]["cmv"] == "60.00"
    assert len(statements) == 7
    assert all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )
    assert not any(
        "FROM produtos" in statement or "UPDATE" in statement
        for statement in statements
    )


def test_batch_chunks_more_than_one_thousand_orders_without_n_plus_one(db):
    tenant, sale_id, _ = scenario(db)
    link(db, tenant, sale_id)
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        with tenant_context(tenant):
            result = get_historical_costs_for_orders(
                db, tenant, MERCHANT, [ORDER] + [f"order-{i}" for i in range(1001)]
            )
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert len(result) == 1002 and result[ORDER]["cmv"] == "60.00"
    assert result["order-1000"]["status"] == "pending"
    assert len(statements) == 9


def canonical_scenario(db):
    tenant, sale_id, item_id = scenario(
        db, quantity="1", cost="43.94", subtotal=65, total=73.9
    )
    db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.id == item_id)
        .values(preco_unitario=65, subtotal=65)
    )
    db.execute(
        IfoodOrder.__table__.insert().values(
            tenant_id=tenant,
            merchant_id=MERCHANT,
            ifood_order_id=ORDER,
            status="CONFIRMED",
            payload={},
        )
    )
    db.execute(
        IfoodPdvBridge.__table__.insert().values(
            tenant_id=tenant,
            merchant_id=MERCHANT,
            ifood_order_id=ORDER,
            sale_id=sale_id,
            reservation_id=1,
            product_id=11,
            quantity=1,
            unit_price=65,
            evidence_hash="a" * 64,
            status="sold",
            actor_id=7,
            stock_decreased_at=NOW,
        )
    )
    return tenant, sale_id, item_id


def test_pdv_bridge_accepts_actual_stock_writer_brasilia_naive_timestamp_without_rewriting(
    db, monkeypatch
):
    tenant, sale_id, item_id = canonical_scenario(db)
    captured = datetime(2026, 10, 24, 20, 54, 53, 850428)
    monkeypatch.setattr("app.vendas.custo_original.now_brasilia", lambda: captured)
    item = SimpleNamespace(
        id=item_id,
        venda_id=sale_id,
        produto_id=11,
        tipo="produto",
        quantidade=Decimal("1"),
        custo_original_saida=None,
    )
    assert registrar_custo_original_saida(
        item,
        [
            {
                "produto_id": 11,
                "movimentacao_id": item_id + 500,
                "quantidade": Decimal("1"),
                "valor_total": Decimal("43.94"),
            }
        ],
        tenant,
    )
    original = deepcopy(item.custo_original_saida)
    assert original["capturado_em"] == "2026-10-24T20:54:53.850428"
    db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.id == item_id)
        .values(custo_original_saida=original)
    )
    result = cost(db, tenant)
    assert result["status"] == "verified" and result["cmv"] == "43.94"
    parsed = datetime.fromisoformat(result["items"][0]["proof_captured_at"])
    assert parsed == captured.replace(tzinfo=BRASILIA_TZ)
    assert parsed.utcoffset().total_seconds() == -3 * 60 * 60
    assert (
        db.execute(select(VendaItem.__table__.c.custo_original_saida)).scalar_one()
        == original
    )
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialSaleLink.__table__)
        ).scalar_one()
        == 0
    )


def test_naive_timestamp_does_not_bypass_original_proof_identifiers(db):
    tenant, sale_id, item_id = canonical_scenario(db)
    proof(
        db,
        item_id,
        capturado_em="2026-10-24T20:54:53.850428",
        venda_item_id=item_id + 1,
    )
    result = cost(db, tenant)
    assert result["cmv"] is None and result["status"] == "pending"


def test_pdv_bridge_reads_original_cmv_without_fabricating_human_link_or_current_cost(
    db,
):
    tenant, sale_id, item_id = canonical_scenario(db)
    before = db.execute(select(VendaItem.__table__.c.custo_original_saida)).scalar_one()
    result = cost(db, tenant)
    assert result["status"] == "verified"
    assert result["cmv"] == "43.94"
    assert result["source"] == "erp_original_stock_out"
    assert result["link"]["source"] == "pdv_bridge"
    assert result["sale"]["id"] == sale_id
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialSaleLink.__table__)
        ).scalar_one()
        == 0
    )
    assert (
        db.execute(select(VendaItem.__table__.c.custo_original_saida)).scalar_one()
        == before
    )
    assert cost(db, tenant) == result
    # Confirmar o mesmo par e idempotente e continua usando a ponte; nao cria
    # um manifesto humano a partir do conjunto atual dos itens.
    assert link(db, tenant, sale_id)["link"]["source"] == "pdv_bridge"
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialSaleLink.__table__)
        ).scalar_one()
        == 0
    )
    with tenant_context(tenant):
        candidates = list_linkable_sales(db, tenant, MERCHANT, str(sale_id))
    assert candidates["sales"][0]["linkable"] is False


@pytest.mark.parametrize(
    "change",
    [
        "price",
        "quantity",
        "product",
        "open_bridge",
        "no_stock_out",
        "proof_id",
        "extra_item",
        "cancel_order",
    ],
)
def test_pdv_bridge_cost_rejects_tampering_or_incomplete_stock_proof(db, change):
    tenant, sale_id, item_id = canonical_scenario(db)
    items, bridges = VendaItem.__table__, IfoodPdvBridge.__table__
    if change == "price":
        db.execute(
            items.update().where(items.c.id == item_id).values(preco_unitario=66)
        )
    elif change == "quantity":
        db.execute(items.update().where(items.c.id == item_id).values(quantidade=2))
    elif change == "product":
        db.execute(items.update().where(items.c.id == item_id).values(produto_id=12))
    elif change == "open_bridge":
        db.execute(
            bridges.update()
            .where(bridges.c.sale_id == sale_id)
            .values(status="reserved")
        )
    elif change == "no_stock_out":
        db.execute(
            bridges.update()
            .where(bridges.c.sale_id == sale_id)
            .values(stock_decreased_at=None)
        )
    elif change == "proof_id":
        proof(db, item_id, venda_item_id=item_id + 1)
    elif change == "extra_item":
        add_item(db, tenant, sale_id, quantity="1", cost="2", product_id=12)
    elif change == "cancel_order":
        db.execute(
            IfoodOrder.__table__.update()
            .where(IfoodOrder.ifood_order_id == ORDER)
            .values(status="CANCELLED")
        )
    result = cost(db, tenant)
    assert result["status"] == "pending" and result["cmv"] is None
    assert result["link"]["source"] == "pdv_bridge"
    assert result["missing"]


def test_pdv_bridge_cannot_be_overridden_by_link_to_another_order(db):
    tenant, sale_id, _ = canonical_scenario(db)
    financial_order(db, tenant, order="another-order")
    with pytest.raises(IfoodFinancialError) as caught:
        link(db, tenant, sale_id, order="another-order")
    assert caught.value.status_code == 409
    # Simula legado inconsistente sem passar pela API protegida.
    db.execute(
        IfoodFinancialSaleLink.__table__.insert().values(
            tenant_id=tenant,
            merchant_id=MERCHANT,
            mode="homologation",
            order_id="another-order",
            venda_id=sale_id,
            source="explicit_confirmation",
            source_note="Registro inconsistente do teste",
            actor_id=7,
            item_manifest=[],
        )
    )
    for order_id in (ORDER, "another-order"):
        result = cost(db, tenant, order=order_id)
        assert result["status"] == "pending" and result["cmv"] is None
        assert result["link"] is not None  # Custo manual nao pode ocultar conflito.


def test_pdv_bridge_cmv_is_not_applied_in_production_or_other_merchant(db, monkeypatch):
    tenant, _, _ = canonical_scenario(db)
    monkeypatch.setattr(
        "app.integrations.ifood.financial_costs.settings.ENVIRONMENT", "production"
    )
    assert cost(db, tenant)["cmv"] is None
    monkeypatch.setattr(
        "app.integrations.ifood.financial_costs.settings.ENVIRONMENT", "test"
    )
    replacement = str(uuid4())
    db.execute(
        IfoodMerchantConfig.__table__.update()
        .where(IfoodMerchantConfig.tenant_id == tenant)
        .values(merchant_id=replacement)
    )
    with tenant_context(tenant):
        result = get_order_historical_cost(db, tenant, replacement, ORDER)
    assert result["cmv"] is None and result["sale"] is None


@pytest.mark.parametrize("alias", ["APP_ENV", "ENV", "ENVIRONMENT"])
@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_alias_estrito_nao_reutiliza_cmv_da_ponte_dev(
    db, monkeypatch, alias, environment
):
    tenant, _, _ = canonical_scenario(db)
    monkeypatch.setattr(
        "app.integrations.ifood.financial_costs.settings.ENVIRONMENT", "test"
    )
    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(alias, environment)
    result = cost(db, tenant)
    assert result["cmv"] is None
    assert result["sale"] is None
    assert result["status"] == "pending"


def complete_financial_fees(db, tenant):
    events = IfoodFinancialEvent.__table__
    snapshot_id = db.execute(
        select(IfoodFinancialSnapshot.__table__.c.id).where(
            IfoodFinancialSnapshot.tenant_id == tenant
        )
    ).scalar_one()
    for position, name, amount in [
        (2, "ORDER_COMMISSION", "-6"),
        (3, "PAYMENT_TRANSACTION_FEE", "-3"),
    ]:
        db.execute(
            events.insert().values(
                tenant_id=tenant,
                snapshot_id=snapshot_id,
                position=position,
                order_id=ORDER,
                name=name,
                trigger="SALE_CONCLUDED",
                amount=Decimal(amount),
                has_transfer_impact=True,
                evidence={},
            )
        )


def manual_costs(db, tenant, cmv=None):
    with tenant_context(tenant):
        return record_order_costs(
            db,
            tenant,
            MERCHANT,
            ORDER,
            dict(
                revenue="100.00",
                cmv=cmv,
                tax="4.00",
                other_costs="1.00",
                source_note="Comprovantes informados DEV",
            ),
            actor_id=7,
        )


def test_financial_report_and_order_use_historical_cmv_without_saving_manual_values(db):
    tenant, sale_id, _ = scenario(db)
    complete_financial_fees(db, tenant)
    link(db, tenant, sale_id)
    result = manual_costs(db, tenant)
    assert result["manual_costs"]["cmv"] is None
    assert result["effective_cmv"] == "60.00"
    assert result["effective_cmv_source"] == "erp_original_stock_out"
    assert result["contribution"]["amount"] == "26.00"
    assert (
        result["contribution"]["label"]
        == "Contribuição com CMV histórico e custos informados"
    )
    assert len(result["events"]) == 3 and result["totals"]["fees"] == "-9.00"
    with tenant_context(tenant):
        order = get_financial_order(db, tenant, MERCHANT, ORDER)
        report = get_financial_report(db, tenant, MERCHANT, NOW.date(), NOW.date())
    assert order == result == report["orders"][0]
    assert (
        db.execute(select(IfoodFinancialOrderCosts.__table__.c.cmv)).scalar_one()
        is None
    )


@pytest.mark.parametrize("manual,expected", [("40.00", "46.00"), ("0.00", "86.00")])
def test_manual_cmv_explicitly_precedes_automatic_even_zero(db, manual, expected):
    tenant, sale_id, _ = scenario(db)
    complete_financial_fees(db, tenant)
    link(db, tenant, sale_id)
    result = manual_costs(db, tenant, manual)
    assert result["historical_cost"]["cmv"] == "60.00"
    assert result["manual_costs"]["cmv"] == manual
    assert result["effective_cmv"] == manual
    assert result["effective_cmv_source"] == "manual"
    assert result["contribution"]["amount"] == expected
    assert result["contribution"]["label"] == "Contribuição com custos informados"
    # Nova versao nula seleciona CMV historico, preservando a anterior.
    result = manual_costs(db, tenant, None)
    assert result["effective_cmv"] == "60.00" and result["manual_costs"]["version"] == 2
    versions = list(
        db.execute(
            select(IfoodFinancialOrderCosts.__table__.c.cmv).order_by(
                IfoodFinancialOrderCosts.version
            )
        ).scalars()
    )
    assert versions == [Decimal(manual), None]


def test_changed_erp_proof_blocks_contribution_even_with_manual_cmv(db):
    tenant, sale_id, item_id = scenario(db)
    complete_financial_fees(db, tenant)
    link(db, tenant, sale_id)
    manual_costs(db, tenant, "40.00")
    proof(db, item_id, custo_total="99.00")
    with tenant_context(tenant):
        result = get_financial_order(db, tenant, MERCHANT, ORDER)
    assert result["effective_cmv_source"] == "manual"
    assert not result["contribution"]["calculated"]
    assert any("mudou" in message for message in result["pending"])


def test_financial_order_retrieval_is_read_only_and_requires_same_scope(db):
    tenant, _, _ = scenario(db)
    with tenant_context(tenant):
        result = get_financial_order(db, tenant, MERCHANT, ORDER)
        with pytest.raises(IfoodFinancialError) as error:
            get_financial_order(db, tenant, MERCHANT, "absent")
    assert error.value.status_code == 404
    assert result["manual_costs"] is None and result["effective_cmv"] is None
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialOrderCosts.__table__)
        ).scalar_one()
        == 0
    )


def test_candidates_are_scoped_search_results_with_no_customer_data_or_auto_choice(db):
    tenant, sale_id, _ = scenario(db)
    legacy_sale, item_id = sale(db, tenant)
    db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.id == item_id)
        .values(custo_original_saida=None)
    )
    sale(db, tenant, canal="app")
    other_tenant = store(db)
    sale(db, other_tenant)
    with tenant_context(tenant):
        result = list_linkable_sales(db, tenant, MERCHANT)
        exact = list_linkable_sales(db, tenant, MERCHANT, search=str(sale_id))
    assert {row["venda_id"] for row in result["sales"]} == {sale_id, legacy_sale}
    assert result["sales"][0]["linkable"] is False
    assert result["sales"][1]["linkable"] is True
    assert exact["sales"][0]["venda_id"] == sale_id
    assert set(exact["sales"][0]) == {
        "venda_id",
        "numero",
        "data",
        "status",
        "linkable",
        "missing",
    }
    assert cost(db, tenant)["sale"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"venda_id": True},
        {"venda_id": "1.0"},
        {"venda_id": 0},
        {"source_note": ""},
        {"source_note": "x" * 1001},
        {"source_note": "\ncontrole"},
        {"actor_id": True},
        {"actor_id": 0},
        {"order_id": "email@example.test"},
        {"mode": "production"},
    ],
)
def test_invalid_link_inputs_never_write(db, overrides):
    tenant, sale_id, _ = scenario(db)
    args = dict(
        db=db,
        tenant_id=tenant,
        merchant_id=MERCHANT,
        order_id=ORDER,
        venda_id=sale_id,
        source_note="Confirmacao explicita DEV",
        actor_id=7,
    )
    args.update(overrides)
    with tenant_context(tenant), pytest.raises(IfoodFinancialError):
        link_order_sale(**args)
    assert (
        db.execute(
            select(func.count()).select_from(IfoodFinancialSaleLink.__table__)
        ).scalar_one()
        == 0
    )


def test_migration_has_force_rls_composite_fk_unique_and_immutable_link():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzzzq20261023a1_ifood_historical_sale_link.py"
    )
    module = runpy.run_path(str(path))
    engine = create_engine("sqlite://")
    # Only existing sale table/index are needed for this migration contract.
    Venda.__table__.create(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP INDEX ux_vendas_tenant_id")
        operations = Operations(MigrationContext.configure(connection))
        module["upgrade"].__globals__["op"] = operations
        module["upgrade"]()
        constraints = inspect(connection).get_unique_constraints(
            "ifood_financial_sale_links"
        )
        assert {c["name"] for c in constraints} == {
            "uq_ifood_fin_sale_link_order",
            "uq_ifood_fin_sale_link_sale",
        }
        fk = inspect(connection).get_foreign_keys("ifood_financial_sale_links")[0]
        assert fk["constrained_columns"] == ["tenant_id", "venda_id"]
        module["downgrade"]()
        assert "ifood_financial_sale_links" not in inspect(connection).get_table_names()
    text = path.read_text(encoding="utf-8")
    assert "apply_tenant_rls(" in text and "enable=True" in text
    assert "BEFORE UPDATE OR DELETE" in text
    assert module["down_revision"] == "zzzzp20261023a1"
    engine.dispose()


def test_database_constraints_block_cross_tenant_or_duplicate_links():
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/zzzzq20261023a1_ifood_historical_sale_link.py"
    )
    module = runpy.run_path(str(path))
    engine = create_engine("sqlite://")
    tenant_a, tenant_b = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql(
            "CREATE TABLE vendas (id INTEGER PRIMARY KEY, tenant_id CHAR(36) NOT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO vendas VALUES (?, ?)", (1, tenant_a.hex)
        )
        operations = Operations(MigrationContext.configure(connection))
        module["upgrade"].__globals__["op"] = operations
        module["upgrade"]()
        table = IfoodFinancialSaleLink.__table__
        values = dict(
            tenant_id=tenant_a,
            merchant_id=MERCHANT,
            mode="homologation",
            order_id=ORDER,
            venda_id=1,
            source="explicit_confirmation",
            source_note="Confirmacao DEV",
            actor_id=7,
            item_manifest=[],
        )
        with pytest.raises(IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                table.insert().values(**dict(values, tenant_id=tenant_b))
            )
        connection.execute(table.insert().values(**values))
        with pytest.raises(IntegrityError, match="UNIQUE"):
            connection.execute(
                table.insert().values(**dict(values, order_id="another-order"))
            )
        with pytest.raises(IntegrityError, match="CHECK"):
            connection.execute(table.insert().values(**dict(values, mode="production")))
    engine.dispose()
