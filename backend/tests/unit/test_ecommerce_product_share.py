"""Public product previews work from the initial HTML, without executing React."""

from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app import produto_identidade_models  # noqa: F401 - register product FK target
from app.models import Tenant
from app.produtos_models import Categoria, Marca, Produto, ProdutoImagem
from app.routes import ecommerce_public
from app.services.ecommerce_product_share import render_product_share_html


BASE_URL = "https://loja.example"
SHARE_PATH = "/ecommerce/compartilhar/produtos/42"


class PreviewHTML(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.meta = {}
        self.links = {}
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        self.tags.append((tag, attributes))
        if tag == "meta":
            self.meta[attributes.get("property") or attributes.get("name")] = (
                attributes.get("content")
            )
        if tag == "link":
            self.links[attributes.get("rel")] = attributes.get("href")


def tenant(**overrides):
    values = {
        "id": "00000000-0000-4000-8000-000000000001",
        "name": "Pet Amigo",
        "ecommerce_slug": "pet-amigo",
        "ecommerce_descricao": "Produtos para seu pet",
        "logo_url": "/uploads/ecommerce/loja.png",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def product(**overrides):
    values = {
        "id": 42,
        "nome": "Ração cães & gatos",
        "descricao": "Alimento completo para seu pet",
        "imagem_principal": "/uploads/produtos/racao.jpg",
        "imagens": [{"url": "/uploads/produtos/segunda.jpg"}],
    }
    values.update(overrides)
    return values


@pytest.fixture
def share_client(monkeypatch):
    app = FastAPI()
    app.include_router(ecommerce_public.router)
    app.dependency_overrides[get_session] = lambda: object()
    for variable in ("ECOMMERCE_PUBLIC_BASE_URL", "ECOMMERCE_BASE_URL", "FRONTEND_URL"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("ECOMMERCE_PUBLIC_BASE_URL", BASE_URL)
    with TestClient(app) as client:
        yield client


def test_initial_html_contains_product_name_image_and_unique_public_url():
    source = render_product_share_html(tenant(), product(), BASE_URL)
    html = PreviewHTML(source)

    assert "Ração cães & gatos" in html.meta["og:title"]
    assert "Pet Amigo" in html.meta["og:title"]
    assert html.meta["og:image"] == f"{BASE_URL}/uploads/produtos/racao.jpg"
    assert html.meta["og:description"] == "Alimento completo para seu pet"
    url = urlsplit(html.meta["og:url"])
    assert f"{url.scheme}://{url.netloc}" == BASE_URL
    assert url.path == f"/api{SHARE_PATH}"
    assert parse_qs(url.query) == {"tenant": ["pet-amigo"]}
    assert "corepet-icon" not in source


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"imagem_principal": None}, "/uploads/produtos/segunda.jpg"),
        ({"imagem_principal": None, "imagens": []}, "/uploads/ecommerce/loja.png"),
        (
            {"imagem_principal": "https://imagens.example/racao.jpg"},
            "https://imagens.example/racao.jpg",
        ),
    ],
)
def test_image_priority_is_product_primary_then_gallery_then_store_logo(
    changes, expected
):
    html = PreviewHTML(
        render_product_share_html(tenant(), product(**changes), BASE_URL)
    )
    assert html.meta["og:image"] == (
        expected if expected.startswith("https://") else BASE_URL + expected
    )


@pytest.mark.parametrize(
    "unsafe",
    ["javascript:alert(1)", "data:image/png;base64,aGVsbG8=", "file:///c:/foto.jpg"],
)
def test_unsafe_image_schemes_are_skipped(unsafe):
    html = PreviewHTML(
        render_product_share_html(tenant(), product(imagem_principal=unsafe), BASE_URL)
    )
    assert html.meta["og:image"] == f"{BASE_URL}/uploads/produtos/segunda.jpg"


def test_missing_product_and_store_images_does_not_use_corepet_logo():
    source = render_product_share_html(
        tenant(logo_url=None), product(imagem_principal=None, imagens=[]), BASE_URL
    )
    html = PreviewHTML(source)
    assert not html.meta.get("og:image")
    assert "corepet-icon" not in source


def test_html_escapes_product_and_store_text_without_injecting_tags():
    dangerous_name = 'Ração "><img src=x onerror=alert(1)> & cães'
    source = render_product_share_html(
        tenant(name='Pet "><script>alert(2)</script>'),
        product(
            nome=dangerous_name, descricao='Texto "><iframe src="https://evil.example">'
        ),
        BASE_URL,
    )
    html = PreviewHTML(source)
    assert dangerous_name in html.meta["og:title"]
    assert not any(tag in {"iframe"} for tag, _ in html.tags)
    assert not any(attributes.get("onerror") for _, attributes in html.tags)
    assert "<script>alert(2)</script>" not in source


def test_store_without_slug_uses_tenant_id_for_public_identity_and_destination():
    store = tenant(ecommerce_slug=None)
    source = render_product_share_html(store, product(), BASE_URL)
    html = PreviewHTML(source)
    assert parse_qs(urlsplit(html.meta["og:url"]).query) == {"tenant": [store.id]}
    destinations = [
        attributes["href"]
        for tag, attributes in html.tags
        if tag == "a" and attributes.get("href")
    ]
    assert destinations
    destination = urlsplit(destinations[0])
    assert f"{destination.scheme}://{destination.netloc}" == BASE_URL
    assert destination.path == "/ecommerce"
    assert parse_qs(destination.query) == {"tenant": [store.id], "produto": ["42"]}


def test_public_route_returns_html_and_forces_ecommerce_visibility(
    share_client, monkeypatch
):
    calls = []
    monkeypatch.setattr(ecommerce_public, "_get_active_tenant", lambda *_: tenant())

    def get_product(**kwargs):
        calls.append(kwargs)
        return product()

    monkeypatch.setattr(ecommerce_public, "obter_produto_publico_por_id", get_product)
    response = share_client.get(
        f"{SHARE_PATH}?tenant=pet-amigo&canal=app&redirect=https://evil.example",
        headers={
            "Host": "evil.example",
            "X-Forwarded-Host": "evil.example",
            "X-Canal-Venda": "app",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "location" not in response.headers
    assert len(calls) == 1
    assert calls[0]["produto_id"] == 42
    assert calls[0]["canal"] == "ecommerce"
    assert calls[0].get("authorization") is None
    assert calls[0].get("x_canal_venda") is None
    html = PreviewHTML(response.text)
    assert html.meta["og:image"] == f"{BASE_URL}/uploads/produtos/racao.jpg"
    assert "evil.example" not in response.text


@pytest.mark.parametrize("status", [403, 404])
def test_share_route_preserves_public_catalog_denials(
    share_client, monkeypatch, status
):
    monkeypatch.setattr(ecommerce_public, "_get_active_tenant", lambda *_: tenant())

    def unavailable(**_kwargs):
        raise HTTPException(status_code=status, detail="Produto indisponível")

    monkeypatch.setattr(ecommerce_public, "obter_produto_publico_por_id", unavailable)
    response = share_client.get(f"{SHARE_PATH}?tenant=pet-amigo")
    assert response.status_code == status
    assert "og:image" not in response.text


@pytest.fixture
def share_catalog(monkeypatch):
    """Real catalog queries against a small, isolated database."""
    from tests.conftest_infra import _get_db_dependencies

    _get_db_dependencies()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (Tenant, Categoria, Marca, Produto, ProdutoImagem):
        model.__table__.create(engine)
    monkeypatch.setattr(
        ecommerce_public.GrupoComercialEstoqueCompartilhadoService,
        "mapa_catalogo_completo_para_consumidora",
        lambda *_args: {},
    )
    monkeypatch.setattr(
        ecommerce_public, "mapear_ofertas_validade_por_produto", lambda *_args: {}
    )
    # PostgreSQL accepts UUID text; SQLite's UUID bind processor requires UUID.
    original_scope = ecommerce_public._escopo_catalogo_publico
    monkeypatch.setattr(
        ecommerce_public,
        "_escopo_catalogo_publico",
        lambda db, tenant_id: original_scope(db, UUID(str(tenant_id))),
    )
    monkeypatch.setenv("ECOMMERCE_PUBLIC_BASE_URL", BASE_URL)
    with Session(engine) as db:
        store_id = uuid4()
        other_id = uuid4()
        db.execute(
            Tenant.__table__.insert(),
            [
                {
                    "id": str(store_id),
                    "name": "Loja A",
                    "name_normalized": "loja a",
                    "status": "active",
                    "ecommerce_slug": "loja-a",
                    "ecommerce_ativo": True,
                    "ecommerce_usar_estoque_canal": False,
                    "ecommerce_ocultar_sem_estoque": False,
                    "ecommerce_ocultar_sem_imagem": False,
                },
                {
                    "id": str(other_id),
                    "name": "Loja B",
                    "name_normalized": "loja b",
                    "status": "active",
                    "ecommerce_slug": "loja-b",
                    "ecommerce_ativo": True,
                    "ecommerce_usar_estoque_canal": False,
                    "ecommerce_ocultar_sem_estoque": False,
                    "ecommerce_ocultar_sem_imagem": False,
                },
            ],
        )

        def add_product(**overrides):
            values = {
                "tenant_id": store_id,
                "user_id": 1,
                "codigo": "SKU-test",
                "nome": "Ração da loja A",
                "ativo": True,
                "situacao": True,
                "is_sellable": True,
                "tipo": "produto",
                "tipo_produto": "SIMPLES",
                "anunciar_ecommerce": True,
                "anunciar_app": True,
                "preco_venda": 20,
                "estoque_atual": 10,
                "imagem_principal": "/uploads/produtos/racao.jpg",
            }
            values.update(overrides)
            result = db.execute(Produto.__table__.insert().values(**values))
            db.flush()
            return result.inserted_primary_key[0]

        app = FastAPI()
        app.include_router(ecommerce_public.router)
        app.dependency_overrides[get_session] = lambda: db
        with TestClient(app) as client:
            yield SimpleNamespace(
                db=db,
                client=client,
                store_id=store_id,
                other_id=other_id,
                add_product=add_product,
            )
    engine.dispose()


@pytest.mark.parametrize(
    "changes",
    [
        {"ativo": False},
        {"anunciar_ecommerce": False, "anunciar_app": True},
        {"preco_venda": 0},
        {"is_sellable": False},
    ],
)
def test_share_does_not_expose_hidden_or_app_only_products(share_catalog, changes):
    product_id = share_catalog.add_product(**changes)
    response = share_catalog.client.get(
        f"/ecommerce/compartilhar/produtos/{product_id}?tenant=loja-a&canal=app"
    )
    assert response.status_code == 404
    assert "Ração da loja A" not in response.text


def test_share_does_not_expose_another_company_product(share_catalog):
    product_id = share_catalog.add_product(
        tenant_id=share_catalog.other_id, nome="Produto privado loja B"
    )
    response = share_catalog.client.get(
        f"/ecommerce/compartilhar/produtos/{product_id}?tenant=loja-a"
    )
    assert response.status_code == 404
    assert "Produto privado loja B" not in response.text


@pytest.mark.parametrize(
    "changes", [{"status": "inactive"}, {"ecommerce_ativo": False}]
)
def test_share_honors_store_status_and_storefront_visibility(share_catalog, changes):
    product_id = share_catalog.add_product()
    share_catalog.db.execute(
        Tenant.__table__.update()
        .where(Tenant.id == str(share_catalog.store_id))
        .values(**changes)
    )
    response = share_catalog.client.get(
        f"/ecommerce/compartilhar/produtos/{product_id}?tenant=loja-a"
    )
    assert response.status_code == 403
    assert "og:image" not in response.text


def test_visible_product_share_is_resolved_from_public_catalog(share_catalog):
    product_id = share_catalog.add_product()
    response = share_catalog.client.get(
        f"/ecommerce/compartilhar/produtos/{product_id}?tenant=loja-a"
    )
    assert response.status_code == 200
    html = PreviewHTML(response.text)
    assert "Ração da loja A" in html.meta["og:title"]
    assert "Loja A" in html.meta["og:title"]
    assert html.meta["og:image"] == f"{BASE_URL}/uploads/produtos/racao.jpg"
