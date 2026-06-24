from pathlib import Path

from app.services import base_catalog_import_core as core
from app.services import base_catalog_import_service as service


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _line_count(*parts: str) -> int:
    return len((BACKEND_DIR / Path(*parts)).read_text(encoding="utf-8").splitlines())


def test_base_catalog_import_service_preserves_public_reexports() -> None:
    assert service.BaseCatalogImportError is core.BaseCatalogImportError
    assert service.BaseCatalogImportResult is core.BaseCatalogImportResult
    assert (
        service.DEFAULT_BASE_CATALOG_BUNDLE_CODE
        == core.DEFAULT_BASE_CATALOG_BUNDLE_CODE
    )
    assert (
        service.DEFAULT_BASE_CATALOG_BUNDLE_VERSION
        == core.DEFAULT_BASE_CATALOG_BUNDLE_VERSION
    )


def test_base_catalog_import_service_stays_split_across_modules() -> None:
    assert _line_count("app", "services", "base_catalog_import_service.py") < 300
    assert _line_count("app", "services", "base_catalog_import_core.py") < 500
    assert _line_count("app", "services", "base_catalog_import_catalog.py") < 1000
    assert _line_count("app", "services", "base_catalog_import_images.py") < 500
    assert _line_count("app", "services", "base_catalog_import_relations.py") < 300
