from pathlib import Path

from app.routes import app_mobile_routes
from app.routes import app_mobile_funcionario_estoque_routes as funcionario_estoque


REPO_ROOT = Path(__file__).resolve().parents[3]


def _non_empty_lines(path: Path) -> int:
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def test_app_mobile_facade_reexports_funcionario_estoque_routes():
    assert (
        app_mobile_routes.FuncionarioProdutoEstoqueResponse
        is funcionario_estoque.FuncionarioProdutoEstoqueResponse
    )
    assert (
        app_mobile_routes.FuncionarioBalancoRequest
        is funcionario_estoque.FuncionarioBalancoRequest
    )
    assert (
        app_mobile_routes.FuncionarioBalancoResponse
        is funcionario_estoque.FuncionarioBalancoResponse
    )

    assert (
        app_mobile_routes._produto_permite_balanco_funcionario
        is funcionario_estoque._produto_permite_balanco_funcionario
    )
    assert (
        app_mobile_routes._serialize_funcionario_produto_estoque
        is funcionario_estoque._serialize_funcionario_produto_estoque
    )
    assert (
        app_mobile_routes._registrar_lote_balanco_funcionario
        is funcionario_estoque._registrar_lote_balanco_funcionario
    )
    assert (
        app_mobile_routes.buscar_produtos_funcionario_estoque
        is funcionario_estoque.buscar_produtos_funcionario_estoque
    )
    assert (
        app_mobile_routes.buscar_produto_funcionario_barcode
        is funcionario_estoque.buscar_produto_funcionario_barcode
    )
    assert (
        app_mobile_routes.registrar_balanco_funcionario_estoque
        is funcionario_estoque.registrar_balanco_funcionario_estoque
    )


def test_app_mobile_router_includes_funcionario_estoque_subrouter():
    route_signatures = {
        (route.path, tuple(sorted(route.methods)))
        for route in app_mobile_routes.router.routes
        if hasattr(route, "methods")
    }

    assert (
        "/app/funcionario/estoque/produtos/buscar",
        ("GET",),
    ) in route_signatures
    assert (
        "/app/funcionario/estoque/produtos/barcode/{barcode}",
        ("GET",),
    ) in route_signatures
    assert ("/app/funcionario/estoque/balanco", ("POST",)) in route_signatures


def test_app_mobile_refactor_keeps_files_below_large_file_threshold():
    paths = [
        REPO_ROOT / "backend/app/routes/app_mobile_routes.py",
        REPO_ROOT / "backend/app/routes/app_mobile_funcionario_estoque_routes.py",
    ]

    counts = {path.name: _non_empty_lines(path) for path in paths}

    assert all(lines < 700 for lines in counts.values())
    assert counts["app_mobile_routes.py"] < 560
    assert counts["app_mobile_funcionario_estoque_routes.py"] < 380
