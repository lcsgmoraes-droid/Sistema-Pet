import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.ecommerceai_integration_models import (
    EcommerceAIConnection,
    EcommerceAIConnectionRequest,
)
from app.empresa_grupo_models import EmpresaGrupoEstoqueCompartilhado
from app.estoque_reserva_service import EstoqueReservaService
from app.models import Tenant
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import (
    PedidoIntegrado,  # noqa: F401 - register FK target for SQLite
)
from app.produtos_models import Produto, ProdutoImagem, ProdutoKitComponente
from app.produto_identity_models import ProdutoSkuAlias
from app.routes.ecommerceai_integration_routes import router
from app.services.ecommerceai_catalog_service import (
    EcommerceAICatalogService,
    marketplace_catalog_read_session,
)
from app.tenancy.context import set_current_tenant


@pytest.fixture
def db_session():
    # Only this contract's actual ORM tables; avoid booting unrelated legacy schemas.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        Tenant,
        Produto,
        ProdutoImagem,
        ProdutoKitComponente,
        ProdutoSkuAlias,
        PedidoIntegradoItem,
        EmpresaGrupoEstoqueCompartilhado,
        EcommerceAIConnectionRequest,
        EcommerceAIConnection,
    ):
        model.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def catalog(db_session):
    tenant_id = uuid4()
    set_current_tenant(tenant_id)
    tenant = Tenant(
        id=str(tenant_id),
        name="Catalog test",
        name_normalized=str(tenant_id),
        ecommerce_usar_estoque_canal=False,
    )
    product = Produto(
        tenant_id=tenant_id,
        user_id=1,
        codigo="SKU-01",
        nome="Racao 10 kg",
        tipo="produto",
        tipo_produto="SIMPLES",
        preco_custo=12.35,
        estoque_atual=10.5,
        estoque_ecommerce=2,
        unidade="UN",
        codigo_barras="7890000000001",
        descricao_completa="Descricao original",
    )
    db_session.add_all([tenant, product])
    db_session.flush()
    service = EcommerceAICatalogService(
        db_session, tenant_id=tenant_id, public_api_url="https://api.corepet.example"
    )
    return service, product, tenant


def test_decimal_contract_and_read_does_not_write(catalog, db_session):
    service, product, _ = catalog
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lstrip().split()[0].upper())

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        result = service.list_products()
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)
    row = result["products"][0]
    assert result["schema_version"] == "corepet.catalog.v1"
    assert result["tenant_id"] == str(product.tenant_id)
    assert (
        datetime.fromisoformat(result["generated_at"]).utcoffset().total_seconds() == 0
    )
    assert row["corepet_id"] == str(product.id)
    assert row["cost"] == {
        "amount": "12.35",
        "currency": "BRL",
        "status": "ready",
        "reason": None,
    }
    assert row["stock"]["physical"] == "10.5"
    assert row["stock"]["reserved"] == "0"
    assert row["stock"]["available"] == "10.5"
    assert row["stock"]["status"] == "ready"
    assert not db_session.dirty
    assert not {"INSERT", "UPDATE", "DELETE"}.intersection(statements)


def test_standard_reservations_use_central_policy_and_clamp_zero(catalog, monkeypatch):
    service, product, _ = catalog
    item = SimpleNamespace(sku=product.codigo, quantidade=12)
    monkeypatch.setattr(
        EstoqueReservaService, "_itens_reservados_ativos", lambda *_: [item]
    )
    row = service.list_products()["products"][0]
    assert row["stock"]["reserved"] == "12"
    assert row["stock"]["available"] == "0"
    assert row["stock"]["physical"] == "10.5"


def test_reservations_aggregate_the_validated_items_once(catalog, monkeypatch):
    service, product, _ = catalog
    calls = []

    def reservations(*_):
        calls.append(True)
        if len(calls) > 1:
            return []  # Simulates reservations finalized after their first read.
        return [
            SimpleNamespace(sku=product.codigo.lower(), quantidade="0.1"),
            SimpleNamespace(sku=product.codigo_barras, quantidade="0.2"),
        ]

    monkeypatch.setattr(EstoqueReservaService, "_itens_reservados_ativos", reservations)
    row = service.list_products()["products"][0]
    assert len(calls) == 1
    assert row["stock"]["reserved"] == "0.3"
    assert row["stock"]["available"] == "10.2"


def test_sqlite_snapshot_keeps_the_injected_session(db_session):
    with marketplace_catalog_read_session(db_session) as snapshot:
        assert snapshot is db_session


@pytest.mark.parametrize("fail", [False, True])
def test_postgres_snapshot_is_readonly_before_any_query_and_closes(monkeypatch, fail):
    from app.services import ecommerceai_catalog_service as module

    calls = []
    db = MagicMock()
    db.get_bind.return_value.dialect.name = "postgresql"
    connection = MagicMock()

    def set_isolation(**kwargs):
        assert kwargs == {"isolation_level": "REPEATABLE READ"}
        calls.append("isolation")
        return connection

    db.get_bind.return_value.engine.connect.return_value.execution_options.side_effect = set_isolation
    connection.__enter__.return_value = connection
    session_factory = MagicMock()
    session = session_factory.return_value.__enter__.return_value

    def execute(statement):
        assert str(statement) == "SET TRANSACTION READ ONLY"
        calls.append("readonly")

    session.execute.side_effect = execute
    monkeypatch.setattr(module, "Session", session_factory)

    def read():
        with marketplace_catalog_read_session(db) as snapshot:
            assert snapshot is session
            calls.append("catalog")
            if fail:
                raise SQLAlchemyError("snapshot failed")

    if fail:
        with pytest.raises(SQLAlchemyError):
            read()
    else:
        read()
    assert calls == ["isolation", "readonly", "catalog"]
    session_factory.assert_called_once_with(
        bind=connection, autoflush=False, expire_on_commit=False
    )
    session_factory.return_value.__exit__.assert_called_once()
    connection.__exit__.assert_called_once()
    db.commit.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"tipo_produto": "KIT", "tipo_kit": "VIRTUAL"}, "kit_policy_unsupported"),
        ({"tipo_produto": "VARIACAO", "tipo_kit": "FISICO"}, "kit_policy_unsupported"),
        ({"tipo_produto": "PAI", "is_parent": True}, "product_type_unsupported"),
        ({"tipo": "servico"}, "service_has_no_stock"),
        ({"e_granel": True}, "bulk_policy_unsupported"),
        ({"estoque_atual": float("nan")}, "stock_value_unavailable"),
    ],
)
def test_unsupported_or_invalid_stock_is_never_ready(catalog, changes, reason):
    service, product, _ = catalog
    for name, value in changes.items():
        setattr(product, name, value)
    row = service._product(
        product,
        channel_stock=False,
        shared_ids=set(),
        reservations={},
        reservation_reason=None,
    )
    assert row["stock"]["status"] == "unavailable"
    assert row["stock"]["available"] is None
    assert row["stock"]["reason"] == reason


def test_channel_and_shared_stock_are_explicitly_unavailable(catalog):
    service, product, _ = catalog
    for channel_stock, shared_ids, reason in [
        (True, set(), "channel_stock_unsupported"),
        (False, {product.id}, "shared_stock_unsupported"),
    ]:
        row = service._product(
            product,
            channel_stock=channel_stock,
            shared_ids=shared_ids,
            reservations={},
            reservation_reason=None,
        )
        assert row["stock"]["reason"] == reason
        assert row["stock"]["physical"] is None
        assert row["cost"]["status"] == "ready"


def test_shared_stock_query_and_tenant_channel_setting(catalog, db_session):
    service, product, tenant = catalog
    tenant.ecommerce_usar_estoque_canal = True
    db_session.flush()
    assert (
        service.list_products()["products"][0]["stock"]["reason"]
        == "channel_stock_unsupported"
    )
    tenant.ecommerce_usar_estoque_canal = False
    shared = EmpresaGrupoEstoqueCompartilhado(
        grupo_id=1,
        empresa_origem_id=str(product.tenant_id),
        produto_origem_id=product.id,
        empresa_consumidora_id=str(uuid4()),
        status="ativo",
        criado_por_usuario_id=1,
    )
    db_session.add(shared)
    db_session.flush()
    assert (
        service.list_products()["products"][0]["stock"]["reason"]
        == "shared_stock_unsupported"
    )
    shared.status = "removido"
    db_session.flush()
    assert service.list_products()["products"][0]["stock"]["status"] == "ready"


def test_missing_virtual_composition_blocks_the_whole_snapshot(
    catalog, db_session, monkeypatch
):
    service, product, _ = catalog
    kit = Produto(
        tenant_id=product.tenant_id,
        user_id=1,
        codigo="KIT",
        nome="Kit",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
    )
    db_session.add(kit)
    db_session.flush()
    monkeypatch.setattr(
        EstoqueReservaService,
        "_itens_reservados_ativos",
        lambda *_: [SimpleNamespace(sku="KIT", quantidade=1)],
    )
    row = service.list_products(q="SKU-01")["products"][0]
    assert row["stock"]["reason"] == "reservation_composition_unverified"
    assert row["stock"]["available"] is None


def _reserved_kit(catalog, db_session, monkeypatch, *, kind="VIRTUAL"):
    service, product, _ = catalog
    kit = Produto(
        tenant_id=product.tenant_id,
        user_id=1,
        codigo="KIT",
        nome="Kit reservado",
        tipo_produto="KIT",
        tipo_kit=kind,
    )
    component_product = Produto(
        tenant_id=product.tenant_id,
        user_id=1,
        codigo="COMPONENT",
        nome="Componente",
        tipo_produto="SIMPLES",
        estoque_atual=20,
    )
    db_session.add_all([kit, component_product])
    db_session.flush()
    component = ProdutoKitComponente(
        tenant_id=product.tenant_id,
        kit_id=kit.id,
        produto_componente_id=component_product.id,
        quantidade=2,
    )
    db_session.add(component)
    db_session.flush()
    monkeypatch.setattr(
        EstoqueReservaService,
        "_itens_reservados_ativos",
        lambda *_: [
            SimpleNamespace(sku="KIT", quantidade=3),
            SimpleNamespace(sku=product.codigo, quantidade=2),
        ],
    )
    return service, product, kit, component_product, component


def test_virtual_reservation_blocks_only_its_verified_components(
    catalog, db_session, monkeypatch
):
    service, product, kit, component_product, _ = _reserved_kit(
        catalog, db_session, monkeypatch
    )
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lstrip().split()[0].upper())

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        rows = {row["corepet_id"]: row for row in service.list_products()["products"]}
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)
    assert rows[str(product.id)]["stock"]["available"] == "8.5"
    assert rows[str(product.id)]["stock"]["reserved"] == "2"
    affected = rows[str(component_product.id)]["stock"]
    assert affected["status"] == "unavailable"
    assert affected["reason"] == "reservation_composition_unsupported"
    assert affected["physical"] is affected["reserved"] is affected["available"] is None
    assert rows[str(kit.id)]["stock"]["reason"] == "kit_policy_unsupported"
    assert not {"INSERT", "UPDATE", "DELETE"}.intersection(statements)
    # Filtering the catalog must not hide active reservations outside that page.
    row = service.list_products(q="COMPONENT")["products"][0]
    assert row["stock"]["reason"] == "reservation_composition_unsupported"


def test_physical_kit_reservation_does_not_reserve_components(
    catalog, db_session, monkeypatch
):
    service, product, _, component_product, _ = _reserved_kit(
        catalog, db_session, monkeypatch, kind="FISICO"
    )
    rows = {row["corepet_id"]: row for row in service.list_products()["products"]}
    assert rows[str(product.id)]["stock"]["available"] == "8.5"
    assert rows[str(component_product.id)]["stock"]["available"] == "20"
    assert rows[str(component_product.id)]["stock"]["reserved"] == "0"


@pytest.mark.parametrize("parent_type", ["KIT", "VARIACAO"])
@pytest.mark.parametrize("component_quantity", [1, 2, 4])
def test_legacy_simple_virtual_component_does_not_block_unrelated_stock(
    catalog, db_session, monkeypatch, parent_type, component_quantity
):
    service, product, kit, component_product, component = _reserved_kit(
        catalog, db_session, monkeypatch
    )
    kit.tipo_produto = parent_type
    component_product.tipo_kit = "VIRTUAL"
    component.quantidade = component_quantity
    db_session.flush()
    assert not EstoqueReservaService._usa_composicao_virtual(component_product)

    reservations, blocked_ids, reason = service._reservations()
    assert reason is None
    assert reservations[product.id] == 2
    assert {kit.id, component_product.id} <= blocked_ids

    rows = {row["corepet_id"]: row for row in service.list_products()["products"]}
    unaffected = rows[str(product.id)]["stock"]
    assert unaffected["status"] == "ready"
    assert unaffected["reserved"] == "2"
    assert unaffected["available"] == "8.5"
    affected = rows[str(component_product.id)]["stock"]
    assert affected["status"] == "unavailable"
    assert affected["physical"] is affected["reserved"] is affected["available"] is None
    # A exceção identifica a folha; não libera sua própria política de estoque.
    assert affected["reason"] == "kit_policy_unsupported"
    assert rows[str(component_product.id)]["cost"]["status"] == "unavailable"
    assert rows[str(kit.id)]["stock"]["status"] == "unavailable"
    assert (
        service.list_products(q="SKU-01")["products"][0]["stock"]["status"] == "ready"
    )


@pytest.mark.parametrize(
    "failure",
    [
        "foreign_component",
        "missing_product",
        "deleted_product",
        "nested_kit",
        "nested_virtual_variation",
        "physical_simple_component",
        "unknown_simple_component_policy",
        "zero_quantity",
        "invalid_quantity",
        "zero_legacy_quantity",
        "invalid_legacy_quantity",
    ],
)
def test_unverified_virtual_composition_still_blocks_unrelated_stock(
    catalog, db_session, monkeypatch, failure
):
    service, _, _, component_product, component = _reserved_kit(
        catalog, db_session, monkeypatch
    )
    if failure == "foreign_component":
        component.tenant_id = uuid4()
    elif failure == "missing_product":
        component.produto_componente_id = 999999
    elif failure == "deleted_product":
        component_product.deleted_at = datetime.now(timezone.utc)
        db_session.flush()
    elif failure == "nested_kit":
        component_product.tipo_produto = "KIT"
        component_product.tipo_kit = "VIRTUAL"
        db_session.flush()
    elif failure == "nested_virtual_variation":
        component_product.tipo_produto = "VARIACAO"
        component_product.tipo_kit = "VIRTUAL"
        db_session.flush()
    elif failure == "physical_simple_component":
        component_product.tipo_kit = "FISICO"
        db_session.flush()
    elif failure == "unknown_simple_component_policy":
        component_product.tipo_kit = "DESCONHECIDO"
        db_session.flush()
    elif failure == "zero_quantity":
        component.quantidade = 0
    elif failure == "invalid_quantity":
        component.quantidade = float("nan")
    elif failure == "zero_legacy_quantity":
        component_product.tipo_kit = "VIRTUAL"
        component.quantidade = 0
        db_session.flush()
    elif failure == "invalid_legacy_quantity":
        component_product.tipo_kit = "VIRTUAL"
        db_session.flush()
        component.quantidade = float("nan")
    row = service.list_products(q="SKU-01")["products"][0]
    assert row["stock"]["reason"] == "reservation_composition_unverified"
    assert row["stock"]["available"] is None


def test_composition_database_failure_cannot_release_unrelated_stock(
    catalog, db_session, monkeypatch
):
    service, *_ = _reserved_kit(catalog, db_session, monkeypatch)

    def fail(*_):
        raise SQLAlchemyError("composition lookup failed")

    monkeypatch.setattr(EstoqueReservaService, "_componentes_por_kit", fail)
    with pytest.raises(SQLAlchemyError):
        service.list_products()


@pytest.mark.parametrize("amount", [None, 0, -1, float("nan"), float("inf")])
def test_unknown_cost_does_not_become_zero(catalog, amount):
    service, product, _ = catalog
    product.preco_custo = amount
    row = service._product(
        product,
        channel_stock=False,
        shared_ids=set(),
        reservations={},
        reservation_reason=None,
    )
    assert row["cost"]["amount"] is None
    assert row["cost"]["status"] == "unavailable"


def test_ambiguous_reservation_alias_fails_closed(catalog, db_session, monkeypatch):
    service, product, _ = catalog
    duplicate = Produto(
        tenant_id=product.tenant_id,
        user_id=1,
        codigo="OTHER",
        nome="Outro",
        codigo_barras=product.codigo,
    )
    db_session.add(duplicate)
    db_session.flush()
    monkeypatch.setattr(
        EstoqueReservaService,
        "_itens_reservados_ativos",
        lambda *_: [SimpleNamespace(sku=product.codigo, quantidade=1)],
    )
    rows = service.list_products()["products"]
    assert all(
        row["stock"]["reason"] == "reservation_identity_unverified" for row in rows
    )
    assert all(row["stock"]["available"] is None for row in rows)


def test_reservation_database_failure_is_not_empty_stock(catalog, monkeypatch):
    service, _, _ = catalog

    def fail(*_):
        raise SQLAlchemyError("test database failure")

    monkeypatch.setattr(EstoqueReservaService, "_itens_reservados_ativos", fail)
    with pytest.raises(SQLAlchemyError):
        service.list_products()


def test_tenant_filter_pagination_and_literal_search(catalog, db_session):
    service, product, _ = catalog
    own = Produto(
        tenant_id=product.tenant_id, user_id=1, codigo="100%", nome="Percentual"
    )
    other = Produto(tenant_id=uuid4(), user_id=1, codigo="OTHER", nome="Racao secreta")
    removed = Produto(
        tenant_id=product.tenant_id,
        user_id=1,
        codigo="OLD",
        nome="Apagado",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([own, removed])
    db_session.flush()
    set_current_tenant(other.tenant_id)
    db_session.add(other)
    db_session.flush()
    set_current_tenant(product.tenant_id)
    result = service.list_products(page_size=1)
    assert result["total"] == 2
    assert result["has_next"] is True
    assert result["products"][0]["corepet_id"] == str(product.id)
    second = service.list_products(page=2, page_size=1)
    assert second["products"][0]["corepet_id"] == str(own.id)
    assert second["has_next"] is False
    assert [row["sku"] for row in service.list_products(q="% ")["products"]] == ["100%"]


def test_gallery_is_absolute_ordered_deduplicated_and_filters_invalid_urls(catalog):
    service, product, _ = catalog
    product.imagem_principal = "/uploads/produtos/main.webp"
    product.imagens = [
        ProdutoImagem(tenant_id=product.tenant_id, url="javascript:bad", ordem=0),
        ProdutoImagem(tenant_id=product.tenant_id, url="http://[", ordem=0),
        ProdutoImagem(
            tenant_id=uuid4(), url="https://other.example/private.jpg", ordem=0
        ),
        ProdutoImagem(
            tenant_id=product.tenant_id, url="https://cdn.example/second.jpg", ordem=2
        ),
        ProdutoImagem(
            tenant_id=product.tenant_id, url="/uploads/produtos/main.webp", ordem=1
        ),
    ]
    media, warnings = service._media(product)
    assert [item["url"] for item in media] == [
        "https://api.corepet.example/uploads/produtos/main.webp",
        "https://cdn.example/second.jpg",
    ]
    assert set(warnings) == {"image_url_unavailable"}


@pytest.fixture
def catalog_http(catalog, db_session):
    service, product, _ = catalog
    raw_token = "cp_eai_" + "z" * 48
    request_id = str(uuid4())
    request = EcommerceAIConnectionRequest(
        request_id=request_id,
        request_nonce=str(uuid4()),
        client_id="ecommerceai",
        ecommerceai_user_id="7",
        callback_url="https://ecommerce.example/callback",
        state="state-with-more-than-32-characters",
        requested_scopes=["catalog:read"],
        status="approved",
        tenant_id=product.tenant_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    connection = EcommerceAIConnection(
        public_id=str(uuid4()),
        request_id=request_id,
        tenant_id=product.tenant_id,
        ecommerceai_user_id="7",
        status="connected",
        scopes=["catalog:read"],
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        token_prefix=raw_token[:16],
    )
    db_session.add_all([request, connection])
    db_session.flush()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client, {"Authorization": f"Bearer {raw_token}"}, connection


def test_http_auth_scope_revocation_and_pagination(catalog_http, db_session):
    client, headers, connection = catalog_http
    path = "/integracoes/ecommerceai/catalog/marketplace-products"
    assert client.get(path).status_code == 401
    assert (
        client.get(path, headers={"Authorization": "Bearer cp_eai_invalid"}).status_code
        == 401
    )
    valid = client.get(path, headers=headers)
    assert valid.status_code == 200
    assert valid.json()["schema_version"] == "corepet.catalog.v1"
    assert client.get(path + "?page_size=201", headers=headers).status_code == 422
    connection.scopes = ["events:write"]
    db_session.flush()
    assert client.get(path, headers=headers).status_code == 403
    connection.scopes = ["catalog:read"]
    connection.revoked_at = datetime.now(timezone.utc)
    db_session.flush()
    assert client.get(path, headers=headers).status_code == 401


def test_http_authorization_and_catalog_share_the_snapshot(catalog_http, monkeypatch):
    from app.routes import ecommerceai_integration_routes as routes
    from app.services import ecommerceai_catalog_service as service_module

    client, headers, _ = catalog_http
    calls = []
    active_session = []
    real_auth = routes._connection_for_token
    real_list = EcommerceAICatalogService.list_products

    @contextmanager
    def snapshot(db):
        calls.append("snapshot_open")
        active_session.append(db)
        try:
            yield db
        finally:
            active_session.clear()
            calls.append("snapshot_closed")

    def authorize(db, authorization):
        assert active_session == [db]
        calls.append("authorize")
        return real_auth(db, authorization)

    def list_products(self, **kwargs):
        assert active_session == [self.db]
        calls.append("catalog")
        return real_list(self, **kwargs)

    monkeypatch.setattr(service_module, "marketplace_catalog_read_session", snapshot)
    monkeypatch.setattr(routes, "_connection_for_token", authorize)
    monkeypatch.setattr(EcommerceAICatalogService, "list_products", list_products)
    response = client.get(
        "/integracoes/ecommerceai/catalog/marketplace-products", headers=headers
    )
    assert response.status_code == 200
    assert calls == ["snapshot_open", "authorize", "catalog", "snapshot_closed"]


def test_http_reservation_failure_returns_unavailable_not_success(
    catalog_http, monkeypatch
):
    client, headers, _ = catalog_http

    def fail(*_):
        raise SQLAlchemyError("private database details")

    monkeypatch.setattr(EstoqueReservaService, "_itens_reservados_ativos", fail)
    result = client.get(
        "/integracoes/ecommerceai/catalog/marketplace-products", headers=headers
    )
    assert result.status_code == 503
    assert "private database details" not in result.text
