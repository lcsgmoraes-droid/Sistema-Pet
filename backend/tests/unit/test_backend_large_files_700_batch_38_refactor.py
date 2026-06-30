from pathlib import Path

from app import comissoes_demonstrativo_admin_routes
from app import comissoes_demonstrativo_routes


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def _method_paths(router):
    return {
        (getattr(route, "path", None), ",".join(sorted(getattr(route, "methods", []))))
        for route in router.routes
    }


def test_comissoes_admin_fatia_38_preserva_api_publica():
    assert (
        comissoes_demonstrativo_routes.listar_funcionarios_comissoes
        is comissoes_demonstrativo_admin_routes.listar_funcionarios_comissoes
    )
    assert (
        comissoes_demonstrativo_routes.fechar_comissoes
        is comissoes_demonstrativo_admin_routes.fechar_comissoes
    )

    assert ("/comissoes/funcionarios", "GET") in _method_paths(
        comissoes_demonstrativo_routes.router
    )
    assert ("/comissoes/fechar", "POST") in _method_paths(
        comissoes_demonstrativo_routes.router
    )


def test_comissoes_routes_agrega_admin_extraido():
    source = _source("backend/app/comissoes_demonstrativo_routes.py")
    admin_source = _source("backend/app/comissoes_demonstrativo_admin_routes.py")

    assert "comissoes_demonstrativo_admin_routes" in source
    assert "router.include_router(admin_router)" in source
    assert "fechar_comissoes_pendentes(" not in source
    assert "COMMISSION_CLOSE_START" not in source
    assert "fechar_comissoes_pendentes(" in admin_source
    assert "COMMISSION_CLOSE_START" in admin_source


def test_comissoes_fatia_38_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        "backend/app/comissoes_demonstrativo_routes.py": _non_empty_line_count(
            "backend/app/comissoes_demonstrativo_routes.py"
        ),
        "backend/app/comissoes_demonstrativo_admin_routes.py": _non_empty_line_count(
            "backend/app/comissoes_demonstrativo_admin_routes.py"
        ),
    }

    assert counts["backend/app/comissoes_demonstrativo_routes.py"] < 700
    assert all(lines < 700 for lines in counts.values())
