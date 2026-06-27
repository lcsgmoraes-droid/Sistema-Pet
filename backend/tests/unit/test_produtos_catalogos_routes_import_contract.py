import importlib
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_catalogos_routes_nao_usa_future_annotations_com_rotas_decoradas():
    source = (BACKEND_ROOT / "app/produtos/catalogos_routes.py").read_text(
        encoding="utf-8"
    )

    assert "from __future__ import annotations" not in source


def test_produtos_routes_importa_catalogos_com_schemas_de_categoria():
    modulo = importlib.import_module("app.produtos_routes")

    assert modulo.catalogos_router is not None
