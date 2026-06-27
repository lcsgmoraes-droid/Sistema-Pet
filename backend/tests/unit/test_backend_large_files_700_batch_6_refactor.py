from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_6_dre_modules_stay_below_limit():
    target_files = [
        "app/dre_routes.py",
        "app/dre_schemas.py",
        "app/dre_calculos.py",
        "app/dre_base_routes.py",
        "app/dre_export_routes.py",
    ]

    for relative_path in target_files:
        path = ROOT / relative_path
        assert path.exists(), (
            f"Missing extracted backend refactor file: {relative_path}"
        )
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_6_dre_routes_is_facade():
    source = read("app/dre_routes.py")

    assert "router.include_router(base_router)" in source
    assert "router.include_router(export_router)" in source
    assert "from .dre_base_routes import" in source
    assert "from .dre_export_routes import" in source
    assert "from .dre_schemas import DREDetalhado, DREResponse" in source
    assert "def gerar_dre(" not in source
    assert "async def exportar_dre_pdf(" not in source
    assert line_count("app/dre_routes.py") <= 120


def test_backend_large_files_700_batch_6_preserves_public_dre_paths():
    from app.dre_routes import router

    route_methods = {
        (route.path, method)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }

    expected_methods = {
        ("/financeiro/dre", "GET"),
        ("/financeiro/dre/detalhado", "GET"),
        ("/financeiro/dre/export/pdf", "GET"),
        ("/financeiro/dre/export/excel", "GET"),
    }

    assert expected_methods <= route_methods


def test_backend_large_files_700_batch_6_keeps_public_exports():
    from app.dre_base_routes import gerar_dre as extracted_gerar_dre
    from app.dre_calculos import calcular_cmv as extracted_calcular_cmv
    from app.dre_export_routes import exportar_dre_pdf as extracted_exportar_pdf
    from app.dre_routes import (
        DREDetalhado,
        DREResponse,
        calcular_cmv,
        exportar_dre_pdf,
        gerar_dre,
    )
    from app.dre_schemas import DREDetalhado as ExtractedDREDetalhado
    from app.dre_schemas import DREResponse as ExtractedDREResponse

    assert DREResponse is ExtractedDREResponse
    assert DREDetalhado is ExtractedDREDetalhado
    assert gerar_dre is extracted_gerar_dre
    assert calcular_cmv is extracted_calcular_cmv
    assert exportar_dre_pdf is extracted_exportar_pdf
