from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_4_contas_receber_router_is_facade():
    source = read("app/contas_receber_routes.py")

    assert "router.include_router(criacao_router)" in source
    assert "router.include_router(consulta_router)" in source
    assert "router.include_router(recebimentos_router)" in source
    assert "router.include_router(recorrencias_router)" in source
    assert line_count("app/contas_receber_routes.py") <= 120


def test_backend_large_files_700_batch_4_modules_stay_below_limit():
    extracted_files = [
        "app/contas_receber_schemas.py",
        "app/contas_receber_recorrencias.py",
        "app/contas_receber_criacao_routes.py",
        "app/contas_receber_consulta_routes.py",
        "app/contas_receber_recebimentos_routes.py",
        "app/contas_receber_recorrencias_routes.py",
    ]

    for relative_path in extracted_files:
        path = ROOT / relative_path
        assert path.exists(), (
            f"Missing extracted backend refactor file: {relative_path}"
        )
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_4_preserves_public_contas_receber_paths():
    from app.contas_receber_routes import router

    route_methods = {
        (route.path, method)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }

    expected_methods = {
        ("/contas-receber/", "POST"),
        ("/contas-receber/", "GET"),
        ("/contas-receber/{conta_id}", "GET"),
        ("/contas-receber/{conta_id}/receber", "POST"),
        ("/contas-receber/dashboard/resumo", "GET"),
        ("/contas-receber/processar-recorrencias", "POST"),
    }

    assert expected_methods <= route_methods


def test_backend_large_files_700_batch_4_keeps_shared_exports():
    from app.contas_receber_recorrencias import (
        calcular_proxima_recorrencia as extracted_helper,
    )
    from app.contas_receber_routes import (
        ContaReceberCreate,
        ContaReceberResponse,
        RecebimentoCreate,
        calcular_proxima_recorrencia,
    )
    from app.contas_receber_schemas import (
        ContaReceberCreate as ExtractedContaReceberCreate,
        ContaReceberResponse as ExtractedContaReceberResponse,
        RecebimentoCreate as ExtractedRecebimentoCreate,
    )

    assert ContaReceberCreate is ExtractedContaReceberCreate
    assert ContaReceberResponse is ExtractedContaReceberResponse
    assert RecebimentoCreate is ExtractedRecebimentoCreate
    assert calcular_proxima_recorrencia is extracted_helper
