"""Ponte iFood/PDV: locks, FIFO e rollback em PostgreSQL descartavel.

Nunca usa DATABASE_URL como destino: requer um banco local dedicado chamado
ifood_pdv_test. Cada execucao cria e remove somente seu schema aleatorio.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import runpy
from threading import Barrier, Event
import time
from types import SimpleNamespace
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
import pytest
from sqlalchemy import Enum, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable


def _migration():
    return runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzt20261024a1_ifood_pdv_pilot.py"
        )
    )


@pytest.fixture(scope="module")
def pg_engine():
    url = os.environ.get("IFOOD_PDV_TEST_POSTGRES_URL")
    if not url:
        pytest.skip(
            "Defina IFOOD_PDV_TEST_POSTGRES_URL para o banco local ifood_pdv_test"
        )
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"localhost", "127.0.0.1"}
    assert parsed.database == "ifood_pdv_test"
    assert (
        make_url(os.environ.get("DATABASE_URL", "sqlite://")).database
        != parsed.database
    )
    schema = f"ifood_pdv_{uuid4().hex}"
    assert re.fullmatch(r"ifood_pdv_[a-f0-9]{32}", schema)
    admin = create_engine(url, pool_pre_ping=True)
    engine = None
    try:
        with admin.begin() as conn:
            assert (
                conn.exec_driver_sql("SELECT current_database()").scalar_one()
                == "ifood_pdv_test"
            )
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(
            url,
            connect_args={
                "options": f"-csearch_path={schema} -capplication_name={schema}"
            },
            pool_pre_ping=True,
            pool_size=6,
            max_overflow=2,
        )
        # Registra os mesmos modelos da API; nenhum lifespan/job e iniciado.
        import app.main  # noqa: F401
        from app.db import Base

        tables = [
            table
            for table in Base.metadata.sorted_tables
            if table.name != "ifood_pdv_bridges"
        ]
        # O metadata legado inclui FK UUID->VARCHAR em modulos alheios ao PDV
        # (ex.: WhatsApp). O baseline usa colunas/PK/uniques/indexes dos modelos;
        # a migration sob teste aplica seus quatro FK compostos e RLS reais.
        with engine.begin() as conn:
            for table in tables:
                for column in table.columns:
                    if isinstance(column.type, Enum):
                        column.type.create(conn, checkfirst=True)
                conn.execute(CreateTable(table, include_foreign_key_constraints=[]))
                for index in table.indexes:
                    conn.execute(CreateIndex(index))
        with engine.begin() as conn:
            # Reconstitui o estado anterior da tabela alterada pela migration.
            # O modelo atual ja declara o novo unique/nullable.
            conn.exec_driver_sql(
                "ALTER TABLE pedidos_integrados DROP CONSTRAINT IF EXISTS uq_pedidos_integrados_tenant_id"
            )
            conn.exec_driver_sql(
                "ALTER TABLE pedidos_integrados ALTER COLUMN pedido_bling_id SET NOT NULL"
            )
            with Operations.context(MigrationContext.configure(conn)):
                _migration()["upgrade"]()
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        # O guard e repetido antes de qualquer cleanup destrutivo.
        assert parsed.database == "ifood_pdv_test"
        assert re.fullmatch(r"ifood_pdv_[a-f0-9]{32}", schema)
        with admin.begin() as conn:
            assert (
                conn.exec_driver_sql("SELECT current_database()").scalar_one()
                == "ifood_pdv_test"
            )
            conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin.dispose()


def _virtual_bag(order_id, merchant_id):
    return {
        "id": order_id,
        "shortCode": "PG01",
        "test": True,
        "merchant": {"id": merchant_id},
        "operationMode": {"type": "TAKEOUT"},
        "bag": {
            "items": [
                {
                    "uniqueId": "one-fixed-item",
                    "name": "Produto ficticio PG",
                    "ean": "7898401961203",
                    "quantity": 1,
                    "product": {"isVariableWeight": False},
                    "unavailable": False,
                    "prices": {"unitValue": {"value": 6500, "currency": "BRL"}},
                }
            ],
            "prices": {"grossValue": {"value": 6500, "currency": "BRL"}},
        },
        "payment": {
            "methods": [
                {
                    "name": "Cash",
                    "inPerson": True,
                    "amount": {"value": 6500, "currency": "BRL"},
                }
            ]
        },
    }


def _configure(monkeypatch, c):
    from app.config import settings

    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "ENVIRONMENT": "test",
        "IFOOD_PDV_PILOT_ENABLED": True,
        "IFOOD_PDV_PILOT_TENANT_ID": str(c.tenant_id),
        "IFOOD_PDV_PILOT_MERCHANT_ID": c.merchant_id,
        "IFOOD_PDV_PILOT_ORDER_ID": c.order_id,
        "IFOOD_PDV_PILOT_SKU": "018631.1",
    }.items():
        monkeypatch.setattr(settings, key, value)


@pytest.fixture
def pilot(pg_engine, monkeypatch):
    from app.caixa_models import Caixa
    from app.estoque_reserva_service import EstoqueReservaService
    from app.ifood_integration_models import IfoodMerchantConfig
    from app.ifood_order_models import IfoodOrder
    from app.models import Tenant, User
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.pedido_integrado_models import PedidoIntegrado
    from app.produtos_models import Produto, ProdutoLote
    from app.tenancy.context import tenant_context

    c = SimpleNamespace(
        engine=pg_engine,
        tenant_id=uuid4(),
        other_tenant=uuid4(),
        merchant_id=str(uuid4()),
        order_id=str(uuid4()),
    )
    _configure(monkeypatch, c)
    with tenant_context(c.tenant_id), Session(pg_engine, expire_on_commit=False) as db:
        db.add(
            Tenant(
                id=str(c.tenant_id),
                name="PG Piloto",
                name_normalized=f"pg-{c.tenant_id}",
            )
        )
        user = User(
            tenant_id=c.tenant_id,
            email=f"{uuid4().hex}@pg.invalid",
            nome="Operador PG",
            hashed_password="not-a-login-secret",
            is_active=True,
            is_admin=True,
        )
        db.add(user)
        db.flush()
        c.user_id = user.id
        product = Produto(
            tenant_id=c.tenant_id,
            user_id=user.id,
            codigo="018631.1",
            nome="Piloto PG",
            codigo_barras="7898401961203",
            gtin_ean="7898401961203",
            unidade="UN",
            tipo="produto",
            tipo_produto="SIMPLES",
            ativo=True,
            estoque_atual=31,
            preco_venda=65,
            preco_custo=43.94,
            descricao_curta="Descricao protegida PG",
        )
        control = Produto(
            tenant_id=c.tenant_id,
            user_id=user.id,
            codigo="CONTROLE-PG",
            nome="Controle PG",
            unidade="UN",
            tipo_produto="SIMPLES",
            ativo=True,
            estoque_atual=19,
            preco_venda=12,
            preco_custo=4,
        )
        db.add_all([product, control])
        db.flush()
        c.product_id, c.control_id = product.id, control.id
        c.lot_ids = []
        for index, qty in enumerate((10, 8, 7, 6), 1):
            lot = ProdutoLote(
                tenant_id=c.tenant_id,
                produto_id=product.id,
                nome_lote=f"PG-{index}",
                quantidade_inicial=qty,
                quantidade_disponivel=qty,
                quantidade_reservada=0,
                status="ativo",
                apenas_identificacao=True,
                ordem_entrada=100 + index,
                custo_unitario=43.94,
                data_validade=datetime(2028, 1, index),
            )
            db.add(lot)
            db.flush()
            c.lot_ids.append(lot.id)
        control_lot = ProdutoLote(
            tenant_id=c.tenant_id,
            produto_id=control.id,
            nome_lote="CONTROLE",
            quantidade_inicial=19,
            quantidade_disponivel=19,
            quantidade_reservada=0,
            status="ativo",
            apenas_identificacao=True,
            ordem_entrada=1,
            custo_unitario=4,
        )
        db.add(control_lot)
        config = IfoodMerchantConfig(
            tenant_id=c.tenant_id, merchant_id=c.merchant_id, active=True
        )
        order = IfoodOrder(
            tenant_id=c.tenant_id,
            merchant_id=c.merchant_id,
            ifood_order_id=c.order_id,
            status="PLACED",
            payload=_virtual_bag(c.order_id, c.merchant_id),
        )
        prior = PedidoIntegrado(
            tenant_id=c.tenant_id,
            pedido_bling_id="ficticio-anterior",
            canal="DEV",
            status="aberto",
            expira_em=PedidoIntegrado.calcular_expiracao(),
            payload={"test": True},
        )
        caixa = Caixa(
            tenant_id=c.tenant_id,
            numero_caixa=1,
            usuario_id=user.id,
            usuario_nome="Operador PG",
            status="aberto",
            valor_abertura=0,
        )
        db.add_all([config, order, prior, caixa])
        db.flush()
        db.add(
            PedidoIntegradoItem(
                tenant_id=c.tenant_id,
                pedido_integrado_id=prior.id,
                sku="018631.1",
                descricao="Reserva anterior",
                quantidade=3,
            )
        )
        c.prior_id, c.caixa_id = prior.id, caixa.id
        db.commit()
        assert (
            EstoqueReservaService.quantidade_reservada_produto(db, c.tenant_id, product)
            == 3
        )
    with (
        tenant_context(c.other_tenant),
        Session(pg_engine, expire_on_commit=False) as db,
    ):
        db.add(
            Tenant(
                id=str(c.other_tenant),
                name="PG Outra",
                name_normalized=f"pg-{c.other_tenant}",
            )
        )
        other_user = User(
            tenant_id=c.other_tenant,
            email=f"{uuid4().hex}@pg.invalid",
            nome="Outro PG",
            hashed_password="not-a-login-secret",
            is_active=True,
        )
        db.add(other_user)
        db.flush()
        other_product = Produto(
            tenant_id=c.other_tenant,
            user_id=other_user.id,
            codigo="018631.1",
            nome="Outra PG",
            codigo_barras="7898401961203",
            unidade="UN",
            tipo_produto="SIMPLES",
            ativo=True,
            estoque_atual=41,
            preco_venda=70,
        )
        db.add(other_product)
        db.flush()
        c.other_product_id = other_product.id
        db.add(
            ProdutoLote(
                tenant_id=c.other_tenant,
                produto_id=other_product.id,
                nome_lote="OUTRO",
                quantidade_inicial=41,
                quantidade_disponivel=41,
                quantidade_reservada=0,
                status="ativo",
                apenas_identificacao=True,
                ordem_entrada=1,
            )
        )
        db.commit()
    # Apenas emissoes/efeitos secundarios posteriores ao commit sao silenciados.
    import app.vendas.finalizacao as finalization

    monkeypatch.setattr(
        finalization, "publicar_eventos_finalizacao", lambda **kwargs: None
    )
    monkeypatch.setattr(
        finalization, "processar_pos_commit_finalizacao", lambda **kwargs: []
    )
    c.control_before = _protected(c)
    return c


def _protected(c):
    from app.produtos_models import Produto, ProdutoLote
    from app.tenancy.context import tenant_context

    def cols(row):
        return {
            column.key: getattr(row, column.key) for column in row.__mapper__.columns
        }

    result = {}
    for tenant_id, product_id in (
        (c.tenant_id, c.control_id),
        (c.other_tenant, c.other_product_id),
    ):
        with tenant_context(tenant_id), Session(c.engine) as db:
            result[str(tenant_id)] = {
                "product": cols(
                    db.query(Produto)
                    .filter(Produto.tenant_id == tenant_id, Produto.id == product_id)
                    .one()
                ),
                "lots": [
                    cols(lot)
                    for lot in db.query(ProdutoLote)
                    .filter(
                        ProdutoLote.tenant_id == tenant_id,
                        ProdutoLote.produto_id == product_id,
                    )
                    .order_by(ProdutoLote.id)
                    .all()
                ],
            }
    return result


def _import(c, barrier=None):
    from app.integrations.ifood.pdv_pilot import import_pdv_pilot
    from app.ifood_order_models import IfoodPdvBridge
    from app.tenancy.context import tenant_context

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        if barrier:
            barrier.wait(timeout=15)
        try:
            import_pdv_pilot(
                db, tenant_id=c.tenant_id, order_id=c.order_id, actor_id=c.user_id
            )
            db.commit()
            bridge = (
                db.query(IfoodPdvBridge)
                .filter(
                    IfoodPdvBridge.tenant_id == c.tenant_id,
                    IfoodPdvBridge.ifood_order_id == c.order_id,
                )
                .one()
            )
            return bridge.sale_id
        except Exception:
            db.rollback()
            raise


def _state(c):
    from app.estoque_reserva_service import EstoqueReservaService
    from app.ifood_order_models import IfoodPdvBridge
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.produtos_models import Produto, ProdutoLote, EstoqueMovimentacao
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda, VendaPagamento

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        product = (
            db.query(Produto)
            .filter(Produto.tenant_id == c.tenant_id, Produto.id == c.product_id)
            .one()
        )
        bridge = (
            db.query(IfoodPdvBridge)
            .filter(
                IfoodPdvBridge.tenant_id == c.tenant_id,
                IfoodPdvBridge.ifood_order_id == c.order_id,
            )
            .first()
        )
        reserve = (
            db.query(PedidoIntegradoItem)
            .filter(
                PedidoIntegradoItem.tenant_id == c.tenant_id,
                PedidoIntegradoItem.pedido_integrado_id == bridge.reservation_id,
            )
            .one()
            if bridge
            else None
        )
        return {
            "physical": product.estoque_atual,
            "reserved": EstoqueReservaService.quantidade_reservada_produto(
                db, c.tenant_id, product
            ),
            "lots": [
                lot.quantidade_disponivel
                for lot in db.query(ProdutoLote)
                .filter(
                    ProdutoLote.tenant_id == c.tenant_id,
                    ProdutoLote.produto_id == c.product_id,
                )
                .order_by(ProdutoLote.ordem_entrada)
                .all()
            ],
            "sales": db.query(Venda).filter(Venda.tenant_id == c.tenant_id).count(),
            "bridges": db.query(IfoodPdvBridge)
            .filter(IfoodPdvBridge.tenant_id == c.tenant_id)
            .count(),
            "reserve_rows": db.query(PedidoIntegradoItem)
            .filter(PedidoIntegradoItem.tenant_id == c.tenant_id)
            .count(),
            "movements": db.query(EstoqueMovimentacao)
            .filter(
                EstoqueMovimentacao.tenant_id == c.tenant_id,
                EstoqueMovimentacao.produto_id == c.product_id,
            )
            .count(),
            "payments": db.query(VendaPagamento)
            .filter(VendaPagamento.tenant_id == c.tenant_id)
            .count(),
            "bridge_status": bridge.status if bridge else None,
            "stock_decreased": bool(bridge and bridge.stock_decreased_at),
            "reserve_sold": bool(reserve and reserve.vendido_em),
            "reserve_released": bool(reserve and reserve.liberado_em),
            "price": product.preco_venda,
            "description": product.descricao_curta,
        }


def _finalize(c, sale_id, barrier=None, fail_after_real_stock=False, stock_gate=None):
    from app.tenancy.context import tenant_context
    from app.vendas.finalizacao import finalizar_venda
    from app.vendas.estoque_baixa import processar_baixa_estoque_item

    def synchronized_real_stock(**kwargs):
        if stock_gate:
            entered, release, identifiers = stock_gate
            identifiers["finalizer_pid"] = (
                kwargs["db"].execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            entered.set()
            assert release.wait(timeout=15)
        result = processar_baixa_estoque_item(**kwargs)
        if fail_after_real_stock:
            raise RuntimeError("PG injected after the actual FIFO decrease")
        return result

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        if barrier:
            barrier.wait(timeout=15)
        return finalizar_venda(
            venda_id=sale_id,
            pagamentos=[{"forma_pagamento": "Dinheiro", "valor": 65}],
            user_id=c.user_id,
            user_nome="Operador PG",
            tenant_id=c.tenant_id,
            db=db,
            caixa_id=c.caixa_id,
            processar_baixa_estoque_item=(
                synchronized_real_stock
                if fail_after_real_stock or stock_gate
                else processar_baixa_estoque_item
            ),
        )


def test_concurrent_import_reserves_once_then_normal_finalizer_consumes_fifo_once(
    pilot,
):
    c = pilot
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_import, c, barrier) for _ in range(2)]
        ids = [future.result(timeout=30) for future in futures]
    assert ids[0] == ids[1]
    assert _state(c) == {
        "physical": 31,
        "reserved": 4,
        "lots": [10, 8, 7, 6],
        "sales": 1,
        "bridges": 1,
        "reserve_rows": 2,
        "movements": 0,
        "payments": 0,
        "bridge_status": "reserved",
        "stock_decreased": False,
        "reserve_sold": False,
        "reserve_released": False,
        "price": 65,
        "description": "Descricao protegida PG",
    }
    result = _finalize(c, ids[0])
    assert result["venda"]["status"] == "finalizada"
    after = _state(c)
    assert (after["physical"], after["reserved"], after["lots"]) == (
        30,
        3,
        [9, 8, 7, 6],
    )
    assert (
        after["sales"],
        after["bridges"],
        after["movements"],
        after["payments"],
    ) == (1, 1, 1, 1)
    assert (
        after["bridge_status"] == "sold"
        and after["stock_decreased"]
        and after["reserve_sold"]
    )
    with pytest.raises(HTTPException):
        _finalize(c, ids[0])
    assert _import(c) == ids[0]
    assert _state(c) == after
    assert _protected(c) == c.control_before


def test_two_simultaneous_finalizations_do_not_decrease_or_receive_twice(pilot):
    c = pilot
    sale_id = _import(c)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_finalize, c, sale_id, barrier) for _ in range(2)]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=30)["venda"]["status"])
            except HTTPException as exc:
                outcomes.append(exc.status_code)
    assert outcomes.count("finalizada") == 1
    assert (
        sum(isinstance(value, int) and value in (400, 409) for value in outcomes) == 1
    )
    state = _state(c)
    assert (
        state["physical"],
        state["reserved"],
        state["lots"],
        state["movements"],
        state["payments"],
    ) == (30, 3, [9, 8, 7, 6], 1, 1)
    assert state["reserve_sold"] and state["stock_decreased"]
    assert _protected(c) == c.control_before


def test_rollback_after_real_fifo_decrease_preserves_reservation_and_allows_one_retry(
    pilot,
):
    c = pilot
    sale_id = _import(c)
    reserved_state = _state(c)
    with pytest.raises(HTTPException) as exc:
        _finalize(c, sale_id, fail_after_real_stock=True)
    assert exc.value.status_code == 500
    assert _state(c) == reserved_state
    _finalize(c, sale_id)
    final = _state(c)
    assert (
        final["physical"],
        final["reserved"],
        final["lots"],
        final["movements"],
        final["payments"],
    ) == (30, 3, [9, 8, 7, 6], 1, 1)
    assert final["reserve_sold"] and final["stock_decreased"]
    assert _protected(c) == c.control_before


def test_import_rollback_has_no_partial_sale_bridge_or_reservation(pilot):
    from app.integrations.ifood.pdv_pilot import import_pdv_pilot
    from app.tenancy.context import tenant_context

    c = pilot
    baseline = _state(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        import_pdv_pilot(
            db, tenant_id=c.tenant_id, order_id=c.order_id, actor_id=c.user_id
        )
        db.flush()
        db.rollback()
    assert _state(c) == baseline
    assert _protected(c) == c.control_before


@pytest.mark.parametrize("operation_type", ["TAKE-OUT", "DELIVERY"])
def test_takeout_alias_and_zero_fee_delivery_keep_one_fifo_decrease_and_marker(
    pilot, operation_type
):
    from app.ifood_order_models import IfoodOrder
    from app.integrations.ifood.pdv_pilot import is_pilot_external_delivery
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda

    c = pilot
    payload = _virtual_bag(c.order_id, c.merchant_id)
    zero = {"value": 0, "currency": "BRL"}
    payload["operationMode"] = {"type": operation_type}
    if operation_type == "DELIVERY":
        payload["operationMode"]["delivery"] = {
            "provider": "IFOOD",
            "prices": {
                "grossValue": dict(zero),
                "discount": dict(zero),
                "netValue": dict(zero),
            },
        }
        payload["fees"] = [
            {
                "prices": {
                    "grossValue": dict(zero),
                    "discount": dict(zero),
                    "netValue": dict(zero),
                }
            }
        ]
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = (
            db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        order.payload = payload
        db.commit()

    sale_id = _import(c)
    reserved = _state(c)
    assert (reserved["physical"], reserved["reserved"], reserved["movements"]) == (
        31,
        4,
        0,
    )
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        sale = (
            db.query(Venda)
            .filter(Venda.tenant_id == c.tenant_id, Venda.id == sale_id)
            .one()
        )
        assert sale.tem_entrega is (operation_type == "DELIVERY")
        assert sale.entregador_id is None and sale.taxa_entrega == 0
        assert sale.tipo_retirada == (
            None if operation_type == "DELIVERY" else "proprio"
        )
        # O mesmo guard usado pelo preflight HTTP dispensa apenas entregador
        # local de uma entrega com origem/bridge de teste realmente validados.
        assert is_pilot_external_delivery(db, sale) is (operation_type == "DELIVERY")

    assert _finalize(c, sale_id)["venda"]["status"] == "finalizada"
    final = _state(c)
    assert (
        final["physical"],
        final["reserved"],
        final["lots"],
        final["movements"],
        final["payments"],
    ) == (30, 3, [9, 8, 7, 6], 1, 1)
    assert (
        final["bridge_status"] == "sold"
        and final["reserve_sold"]
        and final["stock_decreased"]
    )
    assert _import(c) == sale_id
    with pytest.raises(HTTPException):
        _finalize(c, sale_id)
    assert _state(c) == final
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        sale = (
            db.query(Venda)
            .filter(Venda.tenant_id == c.tenant_id, Venda.id == sale_id)
            .one()
        )
        assert is_pilot_external_delivery(db, sale) is False
    assert _protected(c) == c.control_before


def test_committed_cancellation_refreshes_stale_order_before_any_stock_decrease(pilot):
    from app.ifood_order_models import IfoodOrder
    from app.integrations.ifood.orders import upsert_ifood_order
    from app.tenancy.context import tenant_context
    from app.vendas.finalizacao import finalizar_venda
    from app.vendas.estoque_baixa import processar_baixa_estoque_item

    c = pilot
    sale_id = _import(c)
    reserved_state = _state(c)
    stale_loaded, cancellation_committed = Event(), Event()

    def finalize_with_stale_identity_map():
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            stale = (
                db.query(IfoodOrder)
                .filter(
                    IfoodOrder.tenant_id == c.tenant_id,
                    IfoodOrder.ifood_order_id == c.order_id,
                )
                .one()
            )
            assert stale.status == "PLACED"
            stale_loaded.set()
            assert cancellation_committed.wait(timeout=15)
            return finalizar_venda(
                venda_id=sale_id,
                pagamentos=[{"forma_pagamento": "Dinheiro", "valor": 65}],
                user_id=c.user_id,
                user_nome="Operador PG",
                tenant_id=c.tenant_id,
                db=db,
                caixa_id=c.caixa_id,
                processar_baixa_estoque_item=processar_baixa_estoque_item,
            )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(finalize_with_stale_identity_map)
        try:
            assert stale_loaded.wait(timeout=15)
            with tenant_context(c.tenant_id), Session(c.engine) as db:
                upsert_ifood_order(
                    db,
                    tenant_id=c.tenant_id,
                    merchant_id=c.merchant_id,
                    order_id=c.order_id,
                    payload={},
                    event_status="CANCELLED",
                )
                db.commit()
            cancellation_committed.set()
            with pytest.raises(HTTPException) as exc:
                future.result(timeout=30)
            assert exc.value.status_code == 409
        finally:
            cancellation_committed.set()
    assert _state(c) == reserved_state
    assert _protected(c) == c.control_before


def test_concurrent_cancellation_waits_for_order_lock_until_fifo_commit(pilot):
    from app.integrations.ifood.orders import upsert_ifood_order
    from app.tenancy.context import tenant_context

    c = pilot
    sale_id = _import(c)
    stock_entered, release_stock, writer_started = Event(), Event(), Event()
    identifiers = {}

    def persist_cancellation():
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            identifiers["writer_pid"] = db.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()
            writer_started.set()
            upsert_ifood_order(
                db,
                tenant_id=c.tenant_id,
                merchant_id=c.merchant_id,
                order_id=c.order_id,
                payload={},
                event_status="CANCELLED",
            )
            db.flush()  # Leitura/UPDATE real aguardam o lock do finalizador.
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as executor:
        finalization = executor.submit(
            _finalize,
            c,
            sale_id,
            stock_gate=(stock_entered, release_stock, identifiers),
        )
        try:
            assert stock_entered.wait(timeout=15)
            cancellation = executor.submit(persist_cancellation)
            assert writer_started.wait(timeout=15)
            deadline = time.monotonic() + 5
            blocked_by = []
            while time.monotonic() < deadline:
                with c.engine.connect() as conn:
                    blocked_by = conn.execute(
                        text("SELECT pg_blocking_pids(:pid)"),
                        {"pid": identifiers["writer_pid"]},
                    ).scalar_one()
                if identifiers["finalizer_pid"] in blocked_by:
                    break
                time.sleep(0.01)
            assert identifiers["finalizer_pid"] in blocked_by
            assert not cancellation.done()
            release_stock.set()
            assert finalization.result(timeout=30)["venda"]["status"] == "finalizada"
            cancellation.result(timeout=30)
        finally:
            release_stock.set()
    state = _state(c)
    assert (
        state["physical"],
        state["reserved"],
        state["lots"],
        state["movements"],
        state["payments"],
    ) == (30, 3, [9, 8, 7, 6], 1, 1)
    assert state["reserve_sold"] and state["stock_decreased"]
    assert _protected(c) == c.control_before


def test_event_upsert_serializes_confirmed_and_cancelled_before_status_decision(pilot):
    from app.ifood_order_models import IfoodOrder
    from app.integrations.ifood.orders import upsert_ifood_order
    from app.tenancy.context import tenant_context

    c = pilot
    confirmation_ready, release_confirmation, cancellation_started = (
        Event(),
        Event(),
        Event(),
    )
    identifiers = {}
    confirmed_at = datetime.now(timezone.utc)

    def confirm_without_flush():
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            identifiers["confirmation_pid"] = db.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()
            upsert_ifood_order(
                db,
                tenant_id=c.tenant_id,
                merchant_id=c.merchant_id,
                order_id=c.order_id,
                payload={},
                event_status="CONFIRMED",
                event_at=confirmed_at,
            )
            # Sem flush: a leitura FOR UPDATE deve proteger a decisao ANTES
            # de qualquer UPDATE. Um lock apenas na escrita chega tarde.
            confirmation_ready.set()
            assert release_confirmation.wait(timeout=15)
            db.commit()

    def cancel():
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            identifiers["cancellation_pid"] = db.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()
            cancellation_started.set()
            upsert_ifood_order(
                db,
                tenant_id=c.tenant_id,
                merchant_id=c.merchant_id,
                order_id=c.order_id,
                payload={},
                event_status="CANCELLED",
                event_at=confirmed_at + timedelta(seconds=1),
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as executor:
        confirmation = executor.submit(confirm_without_flush)
        try:
            assert confirmation_ready.wait(timeout=15)
            cancellation = executor.submit(cancel)
            assert cancellation_started.wait(timeout=15)
            blocked_by = []
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with c.engine.connect() as conn:
                    blocked_by = conn.execute(
                        text("SELECT pg_blocking_pids(:pid)"),
                        {"pid": identifiers["cancellation_pid"]},
                    ).scalar_one()
                if identifiers["confirmation_pid"] in blocked_by:
                    break
                time.sleep(0.01)
            assert identifiers["confirmation_pid"] in blocked_by
            assert not cancellation.done()
            release_confirmation.set()
            confirmation.result(timeout=30)
            cancellation.result(timeout=30)
        finally:
            release_confirmation.set()
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = (
            db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        assert order.status == "CANCELLED"
    state = _state(c)
    assert (
        state["physical"],
        state["reserved"],
        state["sales"],
        state["bridges"],
        state["movements"],
    ) == (31, 3, 0, 0, 0)
    assert _protected(c) == c.control_before


def test_event_upsert_refreshes_identity_map_so_old_confirmed_cannot_reopen_cancellation(
    pilot,
):
    from app.ifood_order_models import IfoodOrder
    from app.integrations.ifood.orders import upsert_ifood_order
    from app.tenancy.context import tenant_context

    c = pilot
    with (
        tenant_context(c.tenant_id),
        Session(c.engine, expire_on_commit=False) as stale_db,
    ):
        stale = (
            stale_db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        assert stale.status == "PLACED"
        with Session(c.engine) as cancellation_db:
            upsert_ifood_order(
                cancellation_db,
                tenant_id=c.tenant_id,
                merchant_id=c.merchant_id,
                order_id=c.order_id,
                payload={},
                event_status="CANCELLED",
            )
            cancellation_db.commit()
        assert stale.status == "PLACED"  # identidade ORM antiga de outra transacao
        result = upsert_ifood_order(
            stale_db,
            tenant_id=c.tenant_id,
            merchant_id=c.merchant_id,
            order_id=c.order_id,
            payload={},
            event_status="CONFIRMED",
        )
        stale_db.commit()
        assert result.status == "CANCELLED"
    assert _state(c)["physical"] == 31 and _state(c)["reserved"] == 3
    assert _protected(c) == c.control_before


def _emit_bag_event(c, code, full_code):
    from app.ifood_integration_models import IfoodMerchantConfig
    from app.integrations.ifood.orders import process_order_events
    from app.tenancy.context import tenant_context

    event = {
        "id": str(uuid4()),
        "orderId": c.order_id,
        "merchantId": c.merchant_id,
        "code": code,
        "fullCode": full_code,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    acknowledged = []
    client = SimpleNamespace(
        poll_events=lambda merchants: [event],
        acknowledge_events=lambda ids: acknowledged.extend(ids),
    )
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        config = (
            db.query(IfoodMerchantConfig)
            .filter(
                IfoodMerchantConfig.tenant_id == c.tenant_id,
                IfoodMerchantConfig.merchant_id == c.merchant_id,
            )
            .one()
        )
        summary = process_order_events(
            db, tenant_id=c.tenant_id, config=config, client=client
        )
    assert summary["acknowledged"] == 1 and summary["failed"] == 0
    assert acknowledged == [event["id"]]


def _refresh_bag(c, payload):
    from app.ifood_order_models import IfoodOrder
    from app.routes.ifood_order_routes import _refresh_virtual_bag
    from app.tenancy.context import tenant_context

    calls = []

    def get_virtual_bag(order_id):
        assert order_id == c.order_id
        calls.append(order_id)
        # O lock de Order deve cobrir inclusive a leitura externa. O teste
        # usa outra conexao PostgreSQL para comprovar esse limite de verdade.
        with pytest.raises(DBAPIError) as locked:
            with c.engine.begin() as conn:
                conn.execute(
                    text(
                        "SELECT id FROM ifood_orders WHERE tenant_id=CAST(:tenant AS uuid) AND ifood_order_id=:order FOR UPDATE NOWAIT"
                    ),
                    {"tenant": str(c.tenant_id), "order": c.order_id},
                )
        assert locked.value.orig.pgcode == "55P03"
        return deepcopy(payload)

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = (
            db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        result = _refresh_virtual_bag(
            db=db,
            tenant_id=c.tenant_id,
            order=order,
            client=SimpleNamespace(get_virtual_bag=get_virtual_bag),
        )
        last_action = order.last_action
    assert calls == [c.order_id]
    return result, last_action


@pytest.mark.parametrize(
    "code,full_code", [("OPA", "ORDER_PATCHED"), ("SPE", "SEPARATION_ENDED")]
)
def test_processed_bag_event_blocks_old_hash_until_locked_fresh_bag_review(
    pilot, code, full_code
):
    from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
    from app.integrations.ifood.pdv_pilot import pilot_bag_review_reason
    from app.tenancy.context import tenant_context

    c = pilot
    sale_id = _import(c)
    reserved_state = _state(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        bridge = (
            db.query(IfoodPdvBridge)
            .filter(
                IfoodPdvBridge.tenant_id == c.tenant_id,
                IfoodPdvBridge.sale_id == sale_id,
            )
            .one()
        )
        old_hash = bridge.evidence_hash
    _emit_bag_event(c, code, full_code)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = (
            db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        bridge = (
            db.query(IfoodPdvBridge)
            .filter(
                IfoodPdvBridge.tenant_id == c.tenant_id,
                IfoodPdvBridge.sale_id == sale_id,
            )
            .one()
        )
        assert bridge.evidence_hash == old_hash
        assert pilot_bag_review_reason(db, order, bridge)
    with pytest.raises(HTTPException) as invalidated:
        _finalize(c, sale_id)
    assert invalidated.value.status_code == 409
    assert _state(c) == reserved_state

    details, action = _refresh_bag(c, _virtual_bag(c.order_id, c.merchant_id))
    assert action == "pdv_bag_reviewed"
    assert details["pdv_bridge"]["status"] == "reserved"
    assert _finalize(c, sale_id)["venda"]["status"] == "finalizada"
    final = _state(c)
    assert (
        final["physical"],
        final["reserved"],
        final["lots"],
        final["movements"],
        final["payments"],
    ) == (30, 3, [9, 8, 7, 6], 1, 1)
    assert (
        final["bridge_status"] == "sold"
        and final["reserve_sold"]
        and final["stock_decreased"]
    )
    with pytest.raises(HTTPException):
        _finalize(c, sale_id)
    assert _state(c) == final
    assert _protected(c) == c.control_before


@pytest.mark.parametrize("changed_field", ["uniqueId", "quantity"])
def test_changed_fresh_bag_remains_unreviewed_without_recalculating_reservation(
    pilot, changed_field
):
    from app.ifood_order_models import IfoodPdvBridge
    from app.tenancy.context import tenant_context

    c = pilot
    sale_id = _import(c)
    reserved_state = _state(c)
    _emit_bag_event(c, "OPA", "ORDER_PATCHED")
    changed = _virtual_bag(c.order_id, c.merchant_id)
    changed["bag"]["items"][0][changed_field] = (
        "replacement-item" if changed_field == "uniqueId" else 2
    )
    details, action = _refresh_bag(c, changed)
    assert action == "pdv_bag_review_required"
    assert details["pdv_bridge"]["status"] == "reserved"
    with pytest.raises(HTTPException) as still_blocked:
        _finalize(c, sale_id)
    assert still_blocked.value.status_code == 409
    assert _state(c) == reserved_state
    assert _import(c) == sale_id
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        assert (
            db.query(IfoodPdvBridge)
            .filter(IfoodPdvBridge.tenant_id == c.tenant_id)
            .count()
            == 1
        )
    assert _state(c) == reserved_state
    assert _protected(c) == c.control_before


def test_migration_composite_foreign_keys_constraints_and_forced_tenant_rls(pilot):
    from app.ifood_order_models import IfoodPdvBridge
    from app.tenancy.context import tenant_context

    c = pilot
    _import(c)
    inspector = inspect(c.engine)
    foreign_names = {
        foreign["name"] for foreign in inspector.get_foreign_keys("ifood_pdv_bridges")
    }
    assert foreign_names == {
        "fk_ifood_pdv_order",
        "fk_ifood_pdv_sale",
        "fk_ifood_pdv_reservation",
        "fk_ifood_pdv_product",
    }
    assert next(
        column
        for column in inspector.get_columns("pedidos_integrados")
        if column["name"] == "pedido_bling_id"
    )["nullable"]
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        bridge = (
            db.query(IfoodPdvBridge)
            .filter(
                IfoodPdvBridge.tenant_id == c.tenant_id,
                IfoodPdvBridge.ifood_order_id == c.order_id,
            )
            .one()
        )
        for updates in (
            {"product_id": c.other_product_id},
            {"quantity": 2},
            {"unit_price": 0},
        ):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.query(IfoodPdvBridge).filter(
                    IfoodPdvBridge.tenant_id == c.tenant_id,
                    IfoodPdvBridge.id == bridge.id,
                ).update(updates)
                db.flush()
        db.rollback()
    role = f"ifood_pdv_role_{uuid4().hex}"
    with c.engine.connect() as conn:
        transaction = conn.begin()
        try:
            enabled, forced = conn.execute(
                text(
                    "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='ifood_pdv_bridges'::regclass"
                )
            ).one()
            assert enabled and forced
            conn.exec_driver_sql(f'CREATE ROLE "{role}" NOSUPERUSER NOBYPASSRLS')
            conn.exec_driver_sql(
                f'GRANT USAGE ON SCHEMA "{conn.exec_driver_sql("SELECT current_schema()").scalar_one()}" TO "{role}"'
            )
            conn.exec_driver_sql(
                f'GRANT SELECT, UPDATE, DELETE ON ifood_pdv_bridges TO "{role}"'
            )
            conn.exec_driver_sql(f'SET LOCAL ROLE "{role}"')
            for tenant, expected in (
                (str(c.tenant_id), 1),
                (str(c.other_tenant), 0),
                ("", 0),
            ):
                conn.execute(
                    text("SELECT set_config('app.tenant_id',:tenant,true)"),
                    {"tenant": tenant},
                )
                assert (
                    conn.exec_driver_sql(
                        "SELECT count(*) FROM ifood_pdv_bridges"
                    ).scalar_one()
                    == expected
                )
                if tenant != str(c.tenant_id):
                    assert (
                        conn.execute(
                            text(
                                "UPDATE ifood_pdv_bridges SET status='cancelled' WHERE tenant_id=CAST(:tenant AS uuid)"
                            ),
                            {"tenant": str(c.tenant_id)},
                        ).rowcount
                        == 0
                    )
                    assert (
                        conn.execute(
                            text(
                                "DELETE FROM ifood_pdv_bridges WHERE tenant_id=CAST(:tenant AS uuid)"
                            ),
                            {"tenant": str(c.tenant_id)},
                        ).rowcount
                        == 0
                    )
            conn.exec_driver_sql("RESET ROLE")
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="Preserve"):
                    _migration()["downgrade"]()
            assert inspect(conn).has_table("ifood_pdv_bridges")
        finally:
            transaction.rollback()  # inclui o papel SQL temporario
    assert _state(c)["bridge_status"] == "reserved"
    assert _protected(c) == c.control_before
