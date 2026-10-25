"""Sincronizacao DEV do SKU 227 com PostgreSQL e provedor exclusivamente falso.

Reusa o banco descartavel/schema aleatorio do ensaio PDV. O SKU 227 nao participa
do piloto de pedidos iFood (018631.1). Venda/cancelamento normal usam um produto
sem lotes: a recomposicao FIFO do cancelamento generico nao pertence a este piloto.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import runpy
from threading import Event, Lock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from tests.integration.test_ifood_pdv_pilot_postgres import pg_engine  # noqa: F401


BARCODE = "7898242031448"
START = datetime(2030, 1, 2, 12, tzinfo=timezone.utc)


def _migration():
    return runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzv20261024a1_ifood_stock_sync_dev.py"
        )
    )


@pytest.fixture(scope="module")
def stock_pg_engine(request):
    """Aplica a migration real sobre a versao anterior, preservando uma tentativa."""
    engine = request.getfixturevalue("pg_engine")
    from app.ifood_catalog_models import IfoodCatalogLink
    from app.models import Tenant, User
    from app.produtos_models import Produto
    from app.tenancy.context import tenant_context

    # O metadata atual inclui a nova tabela/coluna. Reconstituir somente as duas
    # alteracoes desta migration, no schema descartavel verificado pelo fixture.
    with engine.begin() as conn:
        assert (
            conn.exec_driver_sql("SELECT current_database()").scalar_one()
            == "ifood_pdv_test"
        )
        assert re.fullmatch(
            r"ifood_pdv_[a-f0-9]{32}",
            conn.exec_driver_sql("SELECT current_schema()").scalar_one(),
        )
        conn.exec_driver_sql("DROP TABLE ifood_stock_sync_states")
        conn.exec_driver_sql(
            "ALTER TABLE ifood_catalog_submissions DROP CONSTRAINT ck_ifood_catalog_submission_source"
        )
        conn.exec_driver_sql("ALTER TABLE ifood_catalog_submissions DROP COLUMN source")
    tenant_id = uuid4()
    with tenant_context(tenant_id), Session(engine) as db:
        db.add(
            Tenant(
                id=str(tenant_id), name="Baseline PG", name_normalized=f"pg-{tenant_id}"
            )
        )
        user = User(
            tenant_id=tenant_id,
            email=f"{uuid4().hex}@pg.invalid",
            nome="Baseline",
            hashed_password="not-a-login-secret",
            is_active=True,
        )
        db.add(user)
        db.flush()
        product = Produto(
            tenant_id=tenant_id,
            user_id=user.id,
            codigo="MIGRATION-BASELINE",
            nome="Baseline",
            tipo_produto="SIMPLES",
            ativo=True,
            estoque_atual=7,
            preco_venda=10,
        )
        db.add(product)
        db.flush()
        merchant = str(uuid4())
        link = IfoodCatalogLink(
            tenant_id=tenant_id,
            merchant_id=merchant,
            product_id=product.id,
            barcode=BARCODE,
            mode="existing",
            revision=1,
            portal_checked_at=START,
            portal_checked_by=user.id,
        )
        db.add(link)
        db.flush()
        row_id = db.execute(
            text("""
            INSERT INTO ifood_catalog_submissions
                (tenant_id,link_id,merchant_id,barcode,request_key,operation,fields,
                 payload_hash,evidence,status,actor_id)
            VALUES (:tenant,:link,:merchant,:barcode,:request,'update',
                    CAST(:fields AS json),'0000000000000000000000000000000000000000000000000000000000000000',
                    CAST(:evidence AS json),'accepted',:actor)
            RETURNING id
        """),
            {
                "tenant": tenant_id,
                "link": link.id,
                "merchant": merchant,
                "barcode": BARCODE,
                "request": str(uuid4()),
                "actor": user.id,
                "fields": '["stock"]',
                "evidence": '{"stock":7}',
            },
        ).scalar_one()
        db.commit()
    with engine.begin() as conn:
        before = dict(
            conn.execute(
                text("SELECT * FROM ifood_catalog_submissions WHERE id=:id"),
                {"id": row_id},
            )
            .mappings()
            .one()
        )
        with Operations.context(MigrationContext.configure(conn)):
            _migration()["upgrade"]()
        after = dict(
            conn.execute(
                text("SELECT * FROM ifood_catalog_submissions WHERE id=:id"),
                {"id": row_id},
            )
            .mappings()
            .one()
        )
        assert after.pop("source") == "manual" and after == before
        assert (
            conn.exec_driver_sql(
                "SELECT count(*) FROM ifood_stock_sync_states"
            ).scalar_one()
            == 0
        )
    yield engine


class FakeProvider:
    """Registra o PATCH efetivo sem instanciar qualquer cliente HTTP."""

    def __init__(self):
        self.calls = []
        self.lock = Lock()
        self.entered = None
        self.release = None

    @contextmanager
    def factory(self):
        yield self

    def ingest_items(self, merchant, items, *, method, reset_catalog):
        with self.lock:
            self.calls.append((merchant, deepcopy(items), method, reset_catalog))
        if self.entered is not None:
            self.entered.set()
            assert self.release.wait(timeout=15)
        return {"status_code": 202, "response": {"requestId": str(uuid4())}}


def _product(db, c):
    from app.produtos_models import Produto

    return db.query(Produto).filter_by(tenant_id=c.tenant_id, id=c.product_id).one()


def _snapshot(c):
    from app.produtos_models import Produto, ProdutoLote
    from app.tenancy.context import tenant_context

    result = {}
    for tenant, product_id in (
        (c.tenant_id, c.product_id),
        (c.tenant_id, c.control_id),
        (c.other_tenant, c.other_product_id),
    ):
        with tenant_context(tenant), Session(c.engine) as db:
            row = db.query(Produto).filter_by(tenant_id=tenant, id=product_id).one()
            result[product_id] = {
                col.key: getattr(row, col.key) for col in row.__mapper__.columns
            }
            result[f"lots-{product_id}"] = (
                db.query(ProdutoLote)
                .filter_by(tenant_id=tenant, produto_id=product_id)
                .count()
            )
    return result


def _assert_protected(c):
    after = _snapshot(c)
    for product_id in (c.control_id, c.other_product_id):
        assert after[product_id] == c.before[product_id]
        assert after[f"lots-{product_id}"] == c.before[f"lots-{product_id}"]
    for field in (
        "preco_venda",
        "preco_custo",
        "preco_app",
        "preco_ecommerce",
        "preco_ifood",
        "preco_app_promo",
        "preco_ecommerce_promo",
        "preco_ifood_promo",
        "anunciar_app",
        "anunciar_ecommerce",
    ):
        assert after[c.product_id][field] == c.before[c.product_id][field]
    assert after[f"lots-{c.product_id}"] == 0
    for merchant, items, method, reset in c.provider.calls:
        assert merchant == c.merchant_id
        assert method == "PATCH" and reset is False
        assert items == [
            {"barcode": BARCODE, "inventory": {"stock": items[0]["inventory"]["stock"]}}
        ]


@pytest.fixture
def stock_pilot(request, monkeypatch):
    from app.caixa_models import Caixa
    from app.config import settings
    from app.ifood_catalog_models import IfoodCatalogConfirmation, IfoodCatalogLink
    from app.ifood_integration_models import IfoodMerchantConfig
    from app.models import Tenant, User
    from app.produtos_models import Produto
    from app.tenancy.context import tenant_context

    engine = request.getfixturevalue("stock_pg_engine")
    c = SimpleNamespace(
        engine=engine,
        tenant_id=uuid4(),
        other_tenant=uuid4(),
        merchant_id=str(uuid4()),
        provider=FakeProvider(),
    )
    for tenant, target in ((c.tenant_id, True), (c.other_tenant, False)):
        with tenant_context(tenant), Session(engine) as db:
            db.add(
                Tenant(
                    id=str(tenant), name="PG estoque", name_normalized=f"pg-{tenant}"
                )
            )
            user = User(
                tenant_id=tenant,
                email=f"{uuid4().hex}@pg.invalid",
                nome="PG estoque",
                hashed_password="not-a-login-secret",
                is_active=True,
                is_admin=True,
            )
            db.add(user)
            db.flush()
            product = Produto(
                tenant_id=tenant,
                user_id=user.id,
                codigo="227",
                nome="SKU 227 PG",
                codigo_barras=BARCODE,
                gtin_ean=BARCODE,
                unidade="UN",
                tipo="produto",
                tipo_produto="SIMPLES",
                ativo=True,
                estoque_atual=21 if target else 41,
                preco_venda=142.9,
                preco_custo=100,
                preco_app=143.9,
                preco_ecommerce=144.9,
                preco_ifood=154.9,
                anunciar_ifood=True,
                anunciar_app=True,
                anunciar_ecommerce=True,
            )
            db.add(product)
            db.flush()
            if target:
                c.user_id, c.product_id = user.id, product.id
                control = Produto(
                    tenant_id=tenant,
                    user_id=user.id,
                    codigo="018631.1",
                    nome="Piloto anterior protegido",
                    codigo_barras="7898401961203",
                    gtin_ean="7898401961203",
                    tipo_produto="SIMPLES",
                    ativo=True,
                    estoque_atual=29,
                    preco_venda=65,
                    preco_custo=43.94,
                    anunciar_ifood=True,
                )
                db.add(control)
                caixa = Caixa(
                    tenant_id=tenant,
                    numero_caixa=1,
                    usuario_id=user.id,
                    usuario_nome="PG estoque",
                    status="aberto",
                    valor_abertura=0,
                )
                db.add(caixa)
                db.add(
                    IfoodMerchantConfig(
                        tenant_id=tenant,
                        merchant_id=c.merchant_id,
                        active=True,
                        stock_safety=0,
                    )
                )
                link = IfoodCatalogLink(
                    tenant_id=tenant,
                    merchant_id=c.merchant_id,
                    product_id=product.id,
                    barcode=BARCODE,
                    mode="existing",
                    revision=1,
                    portal_checked_at=START - timedelta(days=1),
                    portal_checked_by=user.id,
                )
                db.add(link)
                db.flush()
                c.control_id, c.caixa_id, c.link_id = control.id, caixa.id, link.id
                db.add(
                    IfoodCatalogConfirmation(
                        tenant_id=tenant,
                        link_id=link.id,
                        barcode=BARCODE,
                        kind="link",
                        present=True,
                        portal_active=True,
                        price=154.9,
                        stock=21,
                        actor_id=user.id,
                        confirmed_at=START - timedelta(days=1),
                    )
                )
                protected_link = IfoodCatalogLink(
                    tenant_id=tenant,
                    merchant_id=c.merchant_id,
                    product_id=control.id,
                    barcode="7898401961203",
                    mode="existing",
                    revision=1,
                    portal_checked_at=START - timedelta(days=1),
                    portal_checked_by=user.id,
                )
                db.add(protected_link)
                db.flush()
                db.add(
                    IfoodCatalogConfirmation(
                        tenant_id=tenant,
                        link_id=protected_link.id,
                        barcode="7898401961203",
                        kind="link",
                        present=True,
                        portal_active=True,
                        price=65,
                        stock=12,
                        actor_id=user.id,
                        confirmed_at=START - timedelta(days=1),
                    )
                )
            else:
                c.other_product_id = product.id
                other_merchant = str(uuid4())
                db.add(
                    IfoodMerchantConfig(
                        tenant_id=tenant, merchant_id=other_merchant, active=True
                    )
                )
                protected_link = IfoodCatalogLink(
                    tenant_id=tenant,
                    merchant_id=other_merchant,
                    product_id=product.id,
                    barcode=BARCODE,
                    mode="existing",
                    revision=1,
                    portal_checked_at=START - timedelta(days=1),
                    portal_checked_by=user.id,
                )
                db.add(protected_link)
                db.flush()
                c.other_link_id = protected_link.id
                db.add(
                    IfoodCatalogConfirmation(
                        tenant_id=tenant,
                        link_id=protected_link.id,
                        barcode=BARCODE,
                        kind="link",
                        present=True,
                        portal_active=True,
                        price=154.9,
                        stock=12,
                        actor_id=user.id,
                        confirmed_at=START - timedelta(days=1),
                    )
                )
            db.commit()
    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "ENVIRONMENT": "test",
        "IFOOD_STOCK_SYNC_DEV_ENABLED": True,
        "IFOOD_STOCK_SYNC_POLLING_ENABLED": True,
        "IFOOD_STOCK_SYNC_TENANT_ID": str(c.tenant_id),
        "IFOOD_STOCK_SYNC_MERCHANT_ID": c.merchant_id,
        "IFOOD_STOCK_SYNC_PRODUCT_ID": c.product_id,
        "IFOOD_STOCK_SYNC_SKU": "227",
        "IFOOD_STOCK_SYNC_BARCODE": BARCODE,
        "IFOOD_CATALOG_WRITE_ENABLED": True,
        "IFOOD_CLIENT_ID": "fake-local-id",
        "IFOOD_CLIENT_SECRET": "fake-local-secret",
        "IFOOD_API_BASE_URL": "http://127.0.0.1:9",
        "IFOOD_PDV_PILOT_ENABLED": False,
    }.items():
        monkeypatch.setattr(settings, key, value)
    import app.domain.events as events
    import app.vendas.finalizacao as finalization

    monkeypatch.setattr(events, "publish_event", lambda event: None)
    monkeypatch.setattr(
        finalization, "publicar_eventos_finalizacao", lambda **kwargs: None
    )
    monkeypatch.setattr(
        finalization, "processar_pos_commit_finalizacao", lambda **kwargs: []
    )
    c.before = _snapshot(c)
    return c


def _tick(c, minutes=0):
    from app.integrations.ifood.stock_sync import poll_ifood_stock_once

    return poll_ifood_stock_once(
        client_factory=c.provider.factory,
        session_factory=lambda: Session(c.engine),
        now=START + timedelta(minutes=minutes),
    )


def _stock(c, value):
    from app.tenancy.context import tenant_context

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        _product(db, c).estoque_atual = value
        db.commit()


def _reserve(c, qty=1):
    from app.pedido_integrado_models import PedidoIntegrado
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.tenancy.context import tenant_context

    with tenant_context(c.tenant_id), Session(c.engine) as db:
        order = PedidoIntegrado(
            tenant_id=c.tenant_id,
            pedido_bling_id=None,
            canal="DEV",
            status="aberto",
            expira_em=PedidoIntegrado.calcular_expiracao(),
            payload={"test": True},
        )
        db.add(order)
        db.flush()
        item = PedidoIntegradoItem(
            tenant_id=c.tenant_id,
            pedido_integrado_id=order.id,
            sku="227",
            descricao="Reserva PG",
            quantidade=qty,
        )
        db.add(item)
        db.commit()
        return item.id


def test_normal_pdv_sale_cancel_and_manual_replenishment_send_stock_only(stock_pilot):
    from app.estoque_entrada_manual_routes import EntradaEstoqueRequest, entrada_estoque
    from app.models import User
    from app.tenancy.context import tenant_context
    from app.vendas.service import VendaService

    c = stock_pilot
    _tick(c)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        sale = VendaService.criar_venda(
            {
                "tenant_id": c.tenant_id,
                "canal": "loja_fisica",
                "caixa_id": c.caixa_id,
                "itens": [
                    {
                        "produto_id": c.product_id,
                        "tipo": "produto",
                        "quantidade": 1,
                        "preco_unitario": 142.9,
                        "subtotal": 142.9,
                    }
                ],
            },
            c.user_id,
            db,
        )
        sale_id = sale["id"]
        assert _product(db, c).estoque_atual == 20
        VendaService.finalizar_venda(
            sale_id,
            [{"forma_pagamento": "Dinheiro", "valor": 142.9}],
            c.user_id,
            "PG estoque",
            c.tenant_id,
            db,
            caixa_id=c.caixa_id,
        )
        assert _product(db, c).estoque_atual == 20
    assert _tick(c, 36)["sent_stock"] == 20
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        VendaService.cancelar_venda(
            sale_id, "Ensaio local de estoque", c.user_id, c.tenant_id, db
        )
        assert _product(db, c).estoque_atual == 21
    assert _tick(c, 72)["sent_stock"] == 21
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        user = db.get(User, c.user_id)
        entrada_estoque(
            EntradaEstoqueRequest(
                produto_id=c.product_id,
                quantidade=2,
                motivo="ajuste",
                custo_unitario=None,
            ),
            db=db,
            user_and_tenant=(user, c.tenant_id),
        )
        assert _product(db, c).estoque_atual == 23
    assert _tick(c, 108)["sent_stock"] == 23
    _assert_protected(c)


def test_reservation_sale_transition_is_not_double_subtracted_and_release_restores(
    stock_pilot,
):
    from app.estoque.service import EstoqueService
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.tenancy.context import tenant_context

    c = stock_pilot
    _tick(c)
    item_id = _reserve(c)
    assert _tick(c, 36)["sent_stock"] == 20
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        EstoqueService.baixar_estoque(
            c.product_id, 1, "venda", 1, "teste_dev", c.user_id, db, str(c.tenant_id)
        )
        db.get(PedidoIntegradoItem, item_id).vendido_em = START.replace(tzinfo=None)
        db.commit()
    assert _tick(c, 72)["status"] == "unchanged"
    second_id = _reserve(c)
    assert _tick(c, 108)["sent_stock"] == 19
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        db.get(PedidoIntegradoItem, second_id).liberado_em = START.replace(tzinfo=None)
        db.commit()
    assert _tick(c, 144)["sent_stock"] == 20
    _assert_protected(c)


def test_uncommitted_sale_and_reservation_rollback_are_invisible_to_worker(stock_pilot):
    from app.estoque.service import EstoqueService
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.pedido_integrado_models import PedidoIntegrado
    from app.tenancy.context import tenant_context

    c = stock_pilot
    _tick(c)
    before = len(c.provider.calls)
    with tenant_context(c.tenant_id), Session(c.engine) as db:
        EstoqueService.baixar_estoque(
            c.product_id, 1, "venda", 1, "teste_dev", c.user_id, db, str(c.tenant_id)
        )
        assert _product(db, c).estoque_atual == 20
        assert _tick(c, 36)["status"] == "unchanged"
        db.rollback()
        order = PedidoIntegrado(
            tenant_id=c.tenant_id,
            pedido_bling_id=None,
            canal="DEV",
            status="aberto",
            expira_em=PedidoIntegrado.calcular_expiracao(),
            payload={"test": True},
        )
        db.add(order)
        db.flush()
        db.add(
            PedidoIntegradoItem(
                tenant_id=c.tenant_id,
                pedido_integrado_id=order.id,
                sku="227",
                descricao="Reserva que sera revertida",
                quantidade=1,
            )
        )
        db.flush()
        assert _tick(c, 37)["status"] == "unchanged"
        db.rollback()
    assert _tick(c, 72)["status"] == "unchanged"
    assert len(c.provider.calls) == before
    _assert_protected(c)


def test_cooldown_coalesces_latest_stock_without_replaying_intermediate_values(
    stock_pilot,
):
    c = stock_pilot
    _tick(c)
    _stock(c, 20)
    assert _tick(c, 36)["sent_stock"] == 20
    count = len(c.provider.calls)
    _stock(c, 19)
    assert _tick(c, 37)["status"] == "cooldown"
    _stock(c, 24)
    assert _tick(c, 38)["status"] == "cooldown"
    assert len(c.provider.calls) == count
    assert _tick(c, 72)["sent_stock"] == 24
    assert _tick(c, 108)["status"] == "unchanged"
    assert len(c.provider.calls) == count + 1
    _assert_protected(c)


def test_two_workers_submit_changed_stock_once(stock_pilot):
    c = stock_pilot
    _tick(c)
    _stock(c, 20)
    c.provider.entered, c.provider.release = Event(), Event()
    before = len(c.provider.calls)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_tick, c, 36)
        assert c.provider.entered.wait(timeout=15)
        second = pool.submit(_tick, c, 36)
        try:
            second_result = second.result(timeout=10)
            assert second_result["status"] in {"busy", "uncertain", "cooldown"}
        finally:
            c.provider.release.set()
        assert first.result(timeout=15)["status"] == "accepted"
    assert len(c.provider.calls) == before + 1
    assert _tick(c, 72)["status"] == "unchanged"
    _assert_protected(c)


def test_stock_change_while_provider_is_slow_is_retained_for_next_window(stock_pilot):
    c = stock_pilot
    _tick(c)
    _stock(c, 20)
    c.provider.entered, c.provider.release = Event(), Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        sending = pool.submit(_tick, c, 36)
        assert c.provider.entered.wait(timeout=15)
        try:
            # A venda pode confirmar enquanto a requisicao anterior esta na rede.
            _stock(c, 19)
        finally:
            c.provider.release.set()
        assert sending.result(timeout=15)["sent_stock"] == 20
    pending = _tick(c, 37)
    assert pending["status"] == "cooldown" and pending["desired_stock"] == 19
    assert _tick(c, 72)["sent_stock"] == 19
    assert _tick(c, 108)["status"] == "unchanged"
    _assert_protected(c)


@contextmanager
def _restricted_engine(c):
    """Papel temporario sem bypass; nenhum papel ou banco existente e alterado."""
    role = f"ifood_stock_role_{uuid4().hex}"
    assert re.fullmatch(r"ifood_stock_role_[a-f0-9]{32}", role)
    restricted = None
    created = False
    try:
        with c.engine.begin() as conn:
            assert (
                conn.exec_driver_sql("SELECT current_database()").scalar_one()
                == "ifood_pdv_test"
            )
            schema = conn.exec_driver_sql("SELECT current_schema()").scalar_one()
            assert re.fullmatch(r"ifood_pdv_[a-f0-9]{32}", schema)
            conn.exec_driver_sql(
                f'CREATE ROLE "{role}" NOSUPERUSER NOBYPASSRLS NOLOGIN'
            )
            conn.exec_driver_sql(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')
            conn.exec_driver_sql(
                f'GRANT SELECT ON ALL TABLES IN SCHEMA "{schema}" TO "{role}"'
            )
            conn.exec_driver_sql(
                f'GRANT INSERT, UPDATE ON ifood_stock_sync_states, ifood_catalog_submissions TO "{role}"'
            )
            # SELECT FOR UPDATE exige UPDATE em pelo menos uma coluna, embora
            # o worker apenas trave a configuracao e nao altere seus campos.
            conn.exec_driver_sql(
                f'GRANT UPDATE (merchant_id) ON ifood_merchant_configs TO "{role}"'
            )
            conn.exec_driver_sql(
                f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "{schema}" TO "{role}"'
            )
        created = True
        restricted = create_engine(
            c.engine.url,
            connect_args={"options": f"-csearch_path={schema} -crole={role}"},
            pool_pre_ping=True,
        )
        with restricted.connect() as conn:
            assert conn.exec_driver_sql("SELECT current_user").scalar_one() == role
            assert (
                conn.execute(
                    text(
                        "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=:role"
                    ),
                    {"role": role},
                ).scalar_one()
                is False
            )
        yield restricted
    finally:
        if restricted is not None:
            restricted.dispose()
        if created:
            with c.engine.begin() as conn:
                assert (
                    conn.exec_driver_sql("SELECT current_database()").scalar_one()
                    == "ifood_pdv_test"
                )
                assert re.fullmatch(r"ifood_stock_role_[a-f0-9]{32}", role)
                conn.exec_driver_sql(f'DROP OWNED BY "{role}"')
                conn.exec_driver_sql(f'DROP ROLE "{role}"')


def test_real_migration_composite_fk_and_rls_survive_worker_commits(stock_pilot):
    from app.ifood_catalog_models import IfoodStockSyncState
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    c = stock_pilot
    assert _tick(c)["status"] == "unchanged"
    assert {
        fk["name"]
        for fk in inspect(c.engine).get_foreign_keys("ifood_stock_sync_states")
    } == {"fk_ifood_stock_sync_link"}
    with tenant_context(c.other_tenant), Session(c.engine) as db:
        db.add(
            IfoodStockSyncState(
                tenant_id=c.other_tenant,
                merchant_id=str(uuid4()),
                link_id=c.other_link_id,
                link_revision=1,
                desired_stock=41,
                status="queued",
                failure_count=0,
            )
        )
        db.commit()
    with _restricted_engine(c) as restricted:
        with restricted.connect() as conn:
            enabled, forced = conn.exec_driver_sql(
                "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='ifood_stock_sync_states'::regclass"
            ).one()
            assert enabled and forced
            conn.execute(
                text("SELECT set_config('app.tenant_id',:tenant,true)"),
                {"tenant": str(c.tenant_id)},
            )
            # SQL cru nao recebe nenhum filtro Python de tenant.
            assert (
                conn.exec_driver_sql(
                    "SELECT count(*) FROM ifood_stock_sync_states"
                ).scalar_one()
                == 1
            )
            assert (
                conn.execute(
                    text(
                        "UPDATE ifood_stock_sync_states SET desired_stock=0 WHERE tenant_id=:tenant"
                    ),
                    {"tenant": c.other_tenant},
                ).rowcount
                == 0
            )
            with pytest.raises(IntegrityError), conn.begin_nested():
                conn.execute(
                    text("""INSERT INTO ifood_stock_sync_states
                    (tenant_id,merchant_id,link_id,link_revision,status,failure_count)
                    VALUES (:tenant,:merchant,:link,1,'queued',0)"""),
                    {
                        "tenant": c.tenant_id,
                        "merchant": c.merchant_id,
                        "link": c.other_link_id,
                    },
                )
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    text("""INSERT INTO ifood_stock_sync_states
                    (tenant_id,merchant_id,link_id,link_revision,status,failure_count)
                    VALUES (:tenant,:merchant,:link,1,'queued',0)"""),
                    {
                        "tenant": c.other_tenant,
                        "merchant": str(uuid4()),
                        "link": c.other_link_id,
                    },
                )
            conn.commit()
            assert conn.exec_driver_sql(
                "SELECT current_setting('app.tenant_id',true)"
            ).scalar_one() in (None, "")
            assert (
                conn.exec_driver_sql(
                    "SELECT count(*) FROM ifood_stock_sync_states"
                ).scalar_one()
                == 0
            )
        with tenant_context(c.tenant_id), Session(restricted) as db:
            sync_rls_tenant(db, c.tenant_id)
            assert (
                db.connection()
                .execute(text("SELECT count(*) FROM ifood_stock_sync_states"))
                .scalar_one()
                == 1
            )
            db.commit()
            assert (
                db.connection()
                .execute(text("SELECT count(*) FROM ifood_stock_sync_states"))
                .scalar_one()
                == 0
            )
            sync_rls_tenant(db, c.tenant_id)
            assert (
                db.connection()
                .execute(text("SELECT count(*) FROM ifood_stock_sync_states"))
                .scalar_one()
                == 1
            )
        admin_engine = c.engine
        _stock(c, 20)
        try:
            c.engine = restricted
            # O worker confirma a tentativa antes da rede e volta a consultar/
            # atualizar a fila depois: SET LOCAL precisa ser reaplicado.
            assert _tick(c, 36)["status"] == "accepted"
            assert _tick(c, 72)["status"] == "unchanged"
        finally:
            c.engine = admin_engine
    _assert_protected(c)
    with c.engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="historico"):
                _migration()["downgrade"]()
        assert inspect(conn).has_table("ifood_stock_sync_states")
        assert "source" in {
            column["name"]
            for column in inspect(conn).get_columns("ifood_catalog_submissions")
        }
