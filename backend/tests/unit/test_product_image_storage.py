import os
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image


os.environ["DEBUG"] = "false"
if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
    os.environ["DATABASE_URL"] = "postgresql://petshop_user:petshop_password@localhost:5432/petshop_db"

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import product_image_storage as storage  # noqa: E402


def _make_png_bytes(size=(2200, 1400), color=(10, 120, 240, 255)):
    image = Image.new("RGBA", size, color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_build_product_thumbnail_url_replaces_originais_segment():
    url = "/uploads/produtos/tenant/15/originais/demo.webp"
    assert (
        storage.build_product_thumbnail_url(url)
        == "/uploads/produtos/tenant/15/thumbs/demo.webp"
    )


def test_prepare_product_image_variants_generates_webp_and_thumbnail():
    prepared = storage.prepare_product_image_variants(
        _make_png_bytes(),
        max_dimension=1000,
        thumbnail_size=240,
        webp_quality=80,
    )

    assert prepared.content_type == "image/webp"
    assert prepared.width <= 1000
    assert prepared.height <= 1000
    assert prepared.original_size_bytes == len(prepared.original_bytes)
    assert len(prepared.thumbnail_bytes) > 0

    with Image.open(BytesIO(prepared.original_bytes)) as original_image:
        assert original_image.format == "WEBP"
        assert original_image.width <= 1000
        assert original_image.height <= 1000

    with Image.open(BytesIO(prepared.thumbnail_bytes)) as thumbnail_image:
        assert thumbnail_image.format == "WEBP"
        assert thumbnail_image.width <= 240
        assert thumbnail_image.height <= 240


def test_save_product_image_variants_local_writes_original_and_thumbnail(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_local_base_dir", lambda: tmp_path / "uploads" / "produtos")
    monkeypatch.setattr(storage, "_local_public_prefix", lambda: "/uploads/produtos")
    monkeypatch.setattr(storage.settings, "PRODUCT_IMAGE_STORAGE_BACKEND", "local")

    prepared = storage.prepare_product_image_variants(
        _make_png_bytes(size=(600, 600)),
        max_dimension=600,
        thumbnail_size=180,
    )

    saved = storage.save_product_image_variants(
        tenant_id="tenant-teste",
        produto_id=42,
        prepared_image=prepared,
        image_token="foto-principal",
    )

    assert saved.url == "/uploads/produtos/tenant-teste/42/originais/foto-principal.webp"
    assert (
        saved.thumbnail_url
        == "/uploads/produtos/tenant-teste/42/thumbs/foto-principal.webp"
    )
    assert saved.image_token == "foto-principal"
    assert (
        tmp_path
        / "uploads"
        / "produtos"
        / "tenant-teste"
        / "42"
        / "originais"
        / "foto-principal.webp"
    ).exists()
    assert (
        tmp_path
        / "uploads"
        / "produtos"
        / "tenant-teste"
        / "42"
        / "thumbs"
        / "foto-principal.webp"
    ).exists()
