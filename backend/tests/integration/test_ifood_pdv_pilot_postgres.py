"""Ponte iFood/PDV: locks, FIFO e rollback em PostgreSQL descartavel.

Nunca usa DATABASE_URL como destino: requer um banco local dedicado chamado
ifood_pdv_test. Cada execucao cria e remove somente seu schema aleatorio.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
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
from sqlalchemy import Enum, create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable


def _migration(filename="zzzzt20261024a1_ifood_pdv_pilot.py"):
    return runpy.run_path(
        str(Path(__file__).parents[2] / "alembic/versions" / filename)
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
        import app.stone_models  # noqa: F401
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
                _migration("zzzzu20261024a1_ifood_pdv_online_evidence.py")["upgrade"]()
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


def _virtual_bag_with_real_delivery_fee(order_id, merchant_id):
    payload = _virtual_bag(order_id, merchant_id)
    payload["operationMode"] = {
        "type": "DELIVERY",
        "delivery": {
            "prices": {
                "grossValue": {"value": 890, "currency": "BRL"},
                "discount": {"value": 0, "currency": "BRL"},
                "netValue": {"value": 890, "currency": "BRL"},
            }
        },
    }
    payload["payment"]["methods"][0]["amount"]["value"] = 7390
    return payload


def _online_virtual_bag(order_id, merchant_id):
    payload = _virtual_bag_with_real_delivery_fee(order_id, merchant_id)
    payload["createdAt"] = datetime.now(timezone.utc).isoformat()
    payload["operationMode"]["delivery"]["provider"] = "MERCHANT"
    payload["payment"]["methods"] = [
        {
            "name": "CREDIT",
            "inPerson": False,
            "liability": "IFOOD",
            "uniqueId": str(uuid4()),
            "amount": {"value": 7589, "currency": "BRL"},
        }
    ]
    payload["fees"] = [
        {
            "audience": "customer",
            "values": [
                {
                    "amount": {"value": 199, "currency": "BRL"},
                    "uniqueId": str(uuid4()),
                    "type": "MERCADO_ATACADO_25V_MIN_199_MAX_399",
                }
            ],
            "prices": {
                "grossValue": {"value": 199, "currency": "BRL"},
                "discount": {"value": 0, "currency": "BRL"},
                "netValue": {"value": 199, "currency": "BRL"},
            },
        }
    ]
    return payload


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


def _finalize(
    c,
    sale_id,
    barrier=None,
    fail_after_real_stock=False,
    stock_gate=None,
    payment_amount=65,
):
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
            pagamentos=[{"forma_pagamento": "Dinheiro", "valor": payment_amount}],
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


@pytest.mark.parametrize("fail_after_fifo", [False, True])
def test_real_delivery_fee_preserves_item_total_payment_and_one_stock_decrease(
    pilot, fail_after_fifo
):
    from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
    from app.integrations.ifood.orders import upsert_ifood_order
    from app.integrations.ifood.pdv_pilot import is_pilot_external_delivery
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda, VendaItem, VendaPagamento

    c = pilot
    payload = _virtual_bag_with_real_delivery_fee(c.order_id, c.merchant_id)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = upsert_ifood_order(
            db,
            tenant_id=c.tenant_id,
            merchant_id=c.merchant_id,
            order_id=c.order_id,
            payload=payload,
            event_status="PLACED",
        )
        assert Decimal(str(order.total)) == Decimal("73.90")
        db.commit()
    sale_id = _import(c)
    assert _import(c) == sale_id
    reserved_state = _state(c)
    assert (
        reserved_state["physical"],
        reserved_state["reserved"],
        reserved_state["sales"],
        reserved_state["bridges"],
        reserved_state["movements"],
    ) == (31, 4, 1, 1, 0)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        sale = (
            db.query(Venda)
            .filter(Venda.tenant_id == c.tenant_id, Venda.id == sale_id)
            .one()
        )
        item = (
            db.query(VendaItem)
            .filter(VendaItem.tenant_id == c.tenant_id, VendaItem.venda_id == sale_id)
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
        assert sale.tem_entrega is True and sale.entregador_id is None
        assert sale.subtotal == Decimal("65.00")
        assert sale.taxa_entrega == Decimal("8.90")
        assert sale.total == Decimal("73.90")
        assert item.quantidade == 1 and item.preco_unitario == item.subtotal == Decimal(
            "65.00"
        )
        assert bridge.quantity == 1 and bridge.unit_price == Decimal("65.00")
        assert is_pilot_external_delivery(db, sale) is True
    # O pagamento cobre a composicao real, sem ignorar o frete nem embuti-lo
    # no preco do unico produto ou em uma segunda unidade.
    with pytest.raises(HTTPException) as underpaid:
        _finalize(c, sale_id, payment_amount=65)
    assert underpaid.value.status_code == 409
    assert _state(c) == reserved_state
    if fail_after_fifo:
        with pytest.raises(HTTPException) as rollback:
            _finalize(c, sale_id, payment_amount=73.90, fail_after_real_stock=True)
        assert rollback.value.status_code == 500
        assert _state(c) == reserved_state

    result = _finalize(c, sale_id, payment_amount=73.90)
    assert result["venda"]["status"] == "finalizada"
    assert result["venda"]["total"] == result["venda"]["total_pago"] == 73.90
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
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        payment = (
            db.query(VendaPagamento)
            .filter(
                VendaPagamento.tenant_id == c.tenant_id,
                VendaPagamento.venda_id == sale_id,
            )
            .one()
        )
        sale = (
            db.query(Venda)
            .filter(Venda.tenant_id == c.tenant_id, Venda.id == sale_id)
            .one()
        )
        assert payment.valor == Decimal("73.90")
        mirrored_order = (
            db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        assert Decimal(str(mirrored_order.total)) == Decimal("73.90")
        assert (
            sale.subtotal == Decimal("65.00")
            and sale.taxa_entrega == Decimal("8.90")
            and sale.total == Decimal("73.90")
        )
    assert _import(c) == sale_id
    with pytest.raises(HTTPException):
        _finalize(c, sale_id, payment_amount=73.90)
    assert _state(c) == final
    assert _protected(c) == c.control_before


def test_real_delivery_fee_display_stays_faithful_after_terminal_event_without_new_sale(
    pilot,
):
    from app.integrations.ifood.orders import upsert_ifood_order
    from app.integrations.ifood.pdv_pilot import import_pdv_pilot
    from app.tenancy.context import tenant_context

    c = pilot
    payload = _virtual_bag_with_real_delivery_fee(c.order_id, c.merchant_id)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = upsert_ifood_order(
            db,
            tenant_id=c.tenant_id,
            merchant_id=c.merchant_id,
            order_id=c.order_id,
            payload=payload,
            event_status="PLACED",
        )
        db.commit()
        assert Decimal(str(order.total)) == Decimal("73.90")
        upsert_ifood_order(
            db,
            tenant_id=c.tenant_id,
            merchant_id=c.merchant_id,
            order_id=c.order_id,
            payload={},
            event_status="CANCELLED",
        )
        db.commit()
        # Uma releitura posterior continua exibindo itens+frete, mas nao pode
        # ressuscitar o pedido ou criar reserva retroativa por causa do total.
        refreshed = upsert_ifood_order(
            db,
            tenant_id=c.tenant_id,
            merchant_id=c.merchant_id,
            order_id=c.order_id,
            payload=payload,
            event_status="CONFIRMED",
        )
        db.commit()
        assert refreshed.status == "CANCELLED"
        assert Decimal(str(refreshed.total)) == Decimal("73.90")
        with pytest.raises(HTTPException) as cancelled:
            import_pdv_pilot(
                db, tenant_id=c.tenant_id, order_id=c.order_id, actor_id=c.user_id
            )
        assert cancelled.value.status_code == 409
        db.rollback()
    state = _state(c)
    assert (
        state["physical"],
        state["reserved"],
        state["sales"],
        state["bridges"],
        state["movements"],
        state["payments"],
    ) == (31, 3, 0, 0, 0, 0)
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
        get_order=lambda order_id: deepcopy(c.online_payload),
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


def _financial_state(c):
    """Prova entradas reais, bancos e POS; nao confunde Vpag com dinheiro recebido."""
    from app.caixa.recebimentos import filtro_recebimentos_caixa
    from app.caixa_models import Caixa
    from app.db import Base
    from app.tenancy.context import tenant_context
    from app.vendas_models import VendaPagamento

    protected_tables = (
        "contas_bancarias",
        "contas_receber",
        "recebimentos",
        "contas_pagar",
        "pagamentos",
        "movimentacoes_bancarias",
        "movimentacoes_financeiras",
        "movimentacoes_caixa",
        "stone_transactions",
        "provisoes_automaticas",
        "lancamentos_manuais",
        "lancamentos_recorrentes",
    )
    result = {}
    for tenant in (c.tenant_id, c.other_tenant):
        with tenant_context(tenant), Session(c.engine) as db:
            result[str(tenant)] = {
                name: [
                    dict(row._mapping)
                    for row in db.execute(
                        select(Base.metadata.tables[name])
                        .where(Base.metadata.tables[name].c.tenant_id == tenant)
                        .order_by(Base.metadata.tables[name].c.id)
                    )
                ]
                for name in protected_tables
            }
            if tenant == c.tenant_id:
                caixa = db.query(Caixa).filter(Caixa.id == c.caixa_id).one()
                result["cash_received"] = (
                    db.query(func.coalesce(func.sum(VendaPagamento.valor), 0))
                    .filter(
                        VendaPagamento.tenant_id == tenant,
                        filtro_recebimentos_caixa(caixa),
                    )
                    .scalar()
                )
    return result


@pytest.fixture
def online_pilot(pilot):
    from app.caixa_models import Caixa
    from app.financeiro_models import ContaBancaria
    from app.ifood_order_models import IfoodOrder
    from app.tenancy.context import tenant_context

    c = pilot
    c.online_payload = _online_virtual_bag(c.order_id, c.merchant_id)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = (
            db.query(IfoodOrder)
            .filter(
                IfoodOrder.tenant_id == c.tenant_id,
                IfoodOrder.ifood_order_id == c.order_id,
            )
            .one()
        )
        order.payload = deepcopy(c.online_payload)
        # Pagamento online nao pode depender de caixa aberto nem usa-lo.
        db.query(Caixa).filter(Caixa.id == c.caixa_id).one().status = "fechado"
        db.add(
            ContaBancaria(
                tenant_id=c.tenant_id,
                user_id=c.user_id,
                nome="Banco ficticio protegido PG",
                tipo="corrente",
                saldo_inicial=123.45,
                saldo_atual=123.45,
                ativa=True,
            )
        )
        db.commit()
    # Evento persistido pelo processador normal, com provider fake em memoria.
    _emit_bag_event(c, "PLC", "PLACED")
    c.financial_before = _financial_state(c)
    assert c.financial_before["cash_received"] == 0
    return c


def _finalize_online(c, *, barrier=None, fail_at=None, tenant_id=None):
    from app.integrations.ifood.pdv_pilot import finalize_online_pdv_pilot
    from app.tenancy.context import tenant_context
    from app.vendas.estoque_baixa import processar_baixa_estoque_item

    tenant_id = tenant_id or c.tenant_id

    def real_fifo_with_failure(**kwargs):
        result = processar_baixa_estoque_item(**kwargs)
        if fail_at == "after_fifo":
            raise RuntimeError("PG online injected after actual FIFO")
        return result

    with tenant_context(tenant_id), Session(c.engine) as db:
        if barrier:
            barrier.wait(timeout=15)
        try:
            order = finalize_online_pdv_pilot(
                db,
                tenant_id=tenant_id,
                order_id=c.order_id,
                actor_id=c.user_id,
                processar_baixa_estoque_item=real_fifo_with_failure,
            )
            if fail_at == "before_commit":
                raise RuntimeError("PG online injected after payment and marker flush")
            db.commit()
            return order.ifood_order_id
        except Exception:
            db.rollback()
            raise


def _assert_online_record(c, sale_id, *, finalized):
    from app.ifood_order_models import IfoodPdvBridge
    from app.tenancy.context import tenant_context
    from app.vendas_models import Venda, VendaPagamento

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        sale = db.query(Venda).filter(Venda.id == sale_id).one()
        bridge = (
            db.query(IfoodPdvBridge)
            .filter(
                IfoodPdvBridge.tenant_id == c.tenant_id,
                IfoodPdvBridge.sale_id == sale_id,
            )
            .one()
        )
        evidence = bridge.online_financial_evidence
        assert (sale.subtotal, sale.taxa_entrega, sale.total) == (
            Decimal("65"),
            Decimal("8.90"),
            Decimal("73.90"),
        )
        assert bridge.unit_price == Decimal("65")
        assert sale.caixa_id is None
        assert sale.status == ("finalizada" if finalized else "aberta")
        assert sale.rentabilidade_snapshot is None and sale.dre_gerada is False
        assert evidence["checkout"] == {
            "items_total": 65.0,
            "delivery_fee": 8.9,
            "ifood_service_fee": 1.99,
            "operational_total": 73.9,
            "customer_total": 75.89,
        }
        assert evidence["receivable"] == {
            "status": "awaiting_financial",
            "gross_amount": 73.9,
            "received_amount": 0,
            "net_amount": None,
            "expected_date": None,
            "margin_status": "pending",
        }
        official_reference = c.online_payload["payment"]["methods"][0]["uniqueId"]
        assert evidence["payment"]["reference"] == official_reference
        assert evidence["payment"]["provider"] == "ifood"
        payments = (
            db.query(VendaPagamento)
            .filter(
                VendaPagamento.tenant_id == c.tenant_id,
                VendaPagamento.venda_id == sale_id,
            )
            .all()
        )
        assert len(payments) == int(finalized)
        if finalized:
            payment = payments[0]
            assert payment.valor == Decimal("73.90")
            assert payment.status == "aprovado"
            assert payment.gateway_provider == "ifood"
            assert payment.gateway_payment_id == official_reference
            assert payment.numero_transacao == official_reference
            assert payment.caixa_id is None
            assert payment.gateway_fee_amount is None
            assert payment.gateway_net_amount is None
            assert payment.gateway_gross_amount is None
            assert payment.data_recebimento_prevista is None
            assert evidence["payment"]["sale_payment_id"] == payment.id
            assert evidence["payment"]["status"] == "approved"
            assert sale.itens[0].custo_original_saida["custo_total"] == "43.94"
        else:
            assert evidence["payment"]["status"] == "platform_responsibility"
    assert _financial_state(c) == c.financial_before
    assert _protected(c) == c.control_before


def test_online_concurrent_import_finalize_and_retry_create_one_payment_and_fifo(
    online_pilot,
):
    c = online_pilot
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        sales = list(executor.map(lambda _: _import(c, barrier), range(2)))
    assert sales[0] == sales[1]
    sale_id = sales[0]
    _assert_online_record(c, sale_id, finalized=False)
    before = _state(c)
    assert (before["physical"], before["reserved"], before["payments"]) == (31, 4, 0)
    # O finalizador comum nao pode cobrar novamente o pagamento online.
    with pytest.raises(HTTPException):
        _finalize(c, sale_id, payment_amount=Decimal("73.90"))
    assert _state(c) == before
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: _finalize_online(c, barrier=barrier), range(2))
        )
    assert results == [c.order_id, c.order_id]
    final = _state(c)
    assert (final["physical"], final["reserved"], final["lots"]) == (
        30,
        3,
        [9, 8, 7, 6],
    )
    assert (
        final["sales"],
        final["bridges"],
        final["movements"],
        final["payments"],
    ) == (1, 1, 1, 1)
    assert final["reserve_sold"] and final["stock_decreased"]
    assert final["bridge_status"] == "sold"
    _assert_online_record(c, sale_id, finalized=True)
    assert _finalize_online(c) == c.order_id
    assert _import(c) == sale_id
    assert _state(c) == final
    _assert_online_record(c, sale_id, finalized=True)


@pytest.mark.parametrize("fail_at", ["after_fifo", "before_commit"])
def test_online_rollback_preserves_fifo_payment_evidence_and_allows_one_retry(
    online_pilot,
    fail_at,
):
    c = online_pilot
    sale_id = _import(c)
    reserved = _state(c)
    with pytest.raises(RuntimeError, match="PG online injected"):
        _finalize_online(c, fail_at=fail_at)
    assert _state(c) == reserved
    _assert_online_record(c, sale_id, finalized=False)
    assert _finalize_online(c) == c.order_id
    assert (_state(c)["physical"], _state(c)["payments"], _state(c)["movements"]) == (
        30,
        1,
        1,
    )
    _assert_online_record(c, sale_id, finalized=True)


@pytest.mark.parametrize(
    "change",
    [
        "item",
        "fee",
        "cancelled",
        "bag_event",
        "tenant",
        "production",
        "missing_feed",
        "unprocessed_feed",
    ],
)
def test_online_changed_payload_events_and_scope_block_before_any_fifo(
    online_pilot,
    monkeypatch,
    change,
):
    from app.config import settings
    from app.ifood_order_models import IfoodEvent, IfoodOrder
    from app.tenancy.context import tenant_context

    c = online_pilot
    sale_id = _import(c)
    before = _state(c)
    if change in {"item", "fee", "cancelled"}:
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            order = (
                db.query(IfoodOrder)
                .filter(
                    IfoodOrder.tenant_id == c.tenant_id,
                    IfoodOrder.ifood_order_id == c.order_id,
                )
                .one()
            )
            changed = deepcopy(order.payload)
            if change == "item":
                changed["bag"]["items"][0]["uniqueId"] = "new-item"
            elif change == "fee":
                changed["fees"][0]["values"][0]["amount"]["value"] = 299
                changed["fees"][0]["prices"]["grossValue"]["value"] = 299
                changed["fees"][0]["prices"]["netValue"]["value"] = 299
                changed["payment"]["methods"][0]["amount"]["value"] = 7689
            else:
                order.status = "CANCELLED"
            order.payload = changed
            db.commit()
    elif change == "bag_event":
        _emit_bag_event(c, "OPA", "ORDER_PATCHED")
    elif change == "production":
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    elif change in {"missing_feed", "unprocessed_feed"}:
        with tenant_context(c.tenant_id), Session(c.engine) as db:
            events = db.query(IfoodEvent).filter(
                IfoodEvent.tenant_id == c.tenant_id,
                IfoodEvent.ifood_order_id == c.order_id,
            )
            if change == "missing_feed":
                events.delete()
            else:
                events.update({"processed_at": None})
            db.commit()
    with pytest.raises(HTTPException) as blocked:
        _finalize_online(c, tenant_id=c.other_tenant if change == "tenant" else None)
    assert blocked.value.status_code == 409
    assert _state(c) == before
    _assert_online_record(c, sale_id, finalized=False)
    if change == "bag_event":
        _, action = _refresh_bag(c, c.online_payload)
        assert action == "pdv_bag_reviewed"
        assert _finalize_online(c) == c.order_id
        _assert_online_record(c, sale_id, finalized=True)


@pytest.mark.parametrize("field", ["valor", "gateway_payment_id"])
def test_online_retry_refuses_changed_payment_without_another_stock_decrease(
    online_pilot,
    field,
):
    from app.tenancy.context import tenant_context
    from app.vendas_models import VendaPagamento

    c = online_pilot
    sale_id = _import(c)
    assert _finalize_online(c) == c.order_id
    final = _state(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        payment = (
            db.query(VendaPagamento)
            .filter(
                VendaPagamento.tenant_id == c.tenant_id,
                VendaPagamento.venda_id == sale_id,
            )
            .one()
        )
        setattr(payment, field, Decimal("74.90") if field == "valor" else str(uuid4()))
        db.commit()
    with pytest.raises(HTTPException) as blocked:
        _finalize_online(c)
    assert blocked.value.status_code == 409
    assert _state(c) == final
    assert _financial_state(c) == c.financial_before
    assert _protected(c) == c.control_before


def test_online_evidence_additive_migration_preserves_cash_and_refuses_data_loss(pilot):
    from app.ifood_order_models import IfoodPdvBridge
    from app.tenancy.context import tenant_context

    c = pilot
    sale_id = _import(c)
    column = next(
        column
        for column in inspect(c.engine).get_columns("ifood_pdv_bridges")
        if column["name"] == "online_financial_evidence"
    )
    assert column["nullable"]
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        bridge = (
            db.query(IfoodPdvBridge)
            .filter(
                IfoodPdvBridge.tenant_id == c.tenant_id,
                IfoodPdvBridge.sale_id == sale_id,
            )
            .one()
        )
        assert bridge.online_financial_evidence is None
        bridge.online_financial_evidence = {"version": 1, "preserve": True}
        db.commit()
    with c.engine.connect() as conn:
        transaction = conn.begin()
        try:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="downgrade recusado"):
                    _migration("zzzzu20261024a1_ifood_pdv_online_evidence.py")[
                        "downgrade"
                    ]()
        finally:
            transaction.rollback()
    assert "online_financial_evidence" in {
        col["name"] for col in inspect(c.engine).get_columns("ifood_pdv_bridges")
    }
    assert _state(c)["physical"] == 31 and _state(c)["payments"] == 0
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
