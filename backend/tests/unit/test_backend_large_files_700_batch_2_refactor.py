from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_2_comissoes_router_is_facade():
    source = read("app/comissoes_routes.py")

    assert "router.include_router(parceiros_router)" in source
    assert "router.include_router(configuracoes_router)" in source
    assert "router.include_router(operacional_router)" in source
    assert line_count("app/comissoes_routes.py") <= 120


def test_backend_large_files_700_batch_2_comissoes_modules_stay_below_limit():
    extracted_files = [
        "app/comissoes_schema_guard.py",
        "app/comissoes_parceiros_routes.py",
        "app/comissoes_configuracoes_routes.py",
        "app/comissoes_operacional_routes.py",
    ]

    for relative_path in extracted_files:
        path = ROOT / relative_path
        assert path.exists(), (
            f"Missing extracted backend refactor file: {relative_path}"
        )
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_2_preserves_public_comissoes_paths():
    from app.comissoes_routes import router

    route_paths = {route.path for route in router.routes}

    expected_paths = {
        "/comissoes/funcionarios",
        "/comissoes/configuracoes/funcionarios",
        "/comissoes/configuracoes/funcionario/{funcionario_id}",
        "/comissoes/configuracoes",
        "/comissoes/configuracoes/batch",
        "/comissoes/configuracoes/{config_id}",
        "/comissoes/configuracoes/duplicar",
        "/comissoes/configuracoes/buscar-aplicavel",
        "/comissoes/itens/pendentes",
        "/comissoes/config-sistema",
        "/comissoes/arvore-produtos",
    }

    assert expected_paths <= route_paths


def test_backend_large_files_700_batch_2_keeps_schema_guard_exported():
    from app.comissoes_routes import ensure_comissoes_config_schema
    from app.comissoes_schema_guard import ensure_comissoes_config_schema as extracted

    assert ensure_comissoes_config_schema is extracted
