import os
import sys
from pathlib import Path
from types import SimpleNamespace


os.environ["DEBUG"] = "false"
if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
    os.environ["DATABASE_URL"] = "postgresql://petshop_user:petshop_password@localhost:5432/petshop_db"

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import bling_product_image_service as service  # noqa: E402
from app.services.product_image_storage import PreparedProductImage, StoredProductImage  # noqa: E402


def test_extract_bling_product_image_url_prioritizes_image_like_fields():
    payload = {
        "nome": "Produto Teste",
        "url": "https://loja.exemplo.com.br/produto/123",
        "imagensExternas": [
            {"link": "https://cdn.exemplo.com.br/produtos/produto-teste.webp"},
        ],
    }

    assert (
        service.extract_bling_product_image_url(payload)
        == "https://cdn.exemplo.com.br/produtos/produto-teste.webp"
    )


def test_extract_bling_product_image_url_accepts_nested_imagem_url_without_extension():
    payload = {
        "midia": {
            "imagemURL": "https://bling-cdn.exemplo.com.br/assets/abc123",
        }
    }

    assert (
        service.extract_bling_product_image_url(payload)
        == "https://bling-cdn.exemplo.com.br/assets/abc123"
    )


def test_attach_remote_image_to_product_marks_first_image_as_primary(monkeypatch):
    prepared = PreparedProductImage(
        original_bytes=b"original",
        thumbnail_bytes=b"thumb",
        width=800,
        height=600,
        original_size_bytes=8,
    )
    stored = StoredProductImage(
        url="/uploads/produtos/tenant-1/42/originais/demo.webp",
        thumbnail_url="/uploads/produtos/tenant-1/42/thumbs/demo.webp",
        image_token="demo",
    )

    monkeypatch.setattr(service, "_download_remote_image_bytes", lambda image_url: b"conteudo")
    monkeypatch.setattr(service, "prepare_product_image_variants", lambda file_bytes: prepared)
    monkeypatch.setattr(service, "save_product_image_variants", lambda **kwargs: stored)

    fake_db = SimpleNamespace(added=[])
    fake_db.add = lambda obj: fake_db.added.append(obj)

    produto = SimpleNamespace(
        id=42,
        imagem_principal=None,
        imagens=[],
    )

    imagem = service.attach_remote_image_to_product(
        fake_db,
        tenant_id="tenant-1",
        produto=produto,
        image_url="https://cdn.exemplo.com.br/demo.jpg",
    )

    assert imagem.e_principal is True
    assert imagem.url == stored.url
    assert produto.imagem_principal == stored.url
    assert fake_db.added == [imagem]
