from pathlib import Path
import importlib
import os


os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


BACKEND_ROOT = Path(__file__).resolve().parents[2]

TARGET_FILES = [
    "app/notas_entrada_routes.py",
    "app/comissoes_routes.py",
    "app/analise_racoes_routes.py",
    "app/conciliacao_aba1_routes.py",
    "app/produtos/relatorios_routes.py",
]

EXTRACTED_MODULES = [
    "app.notas_entrada.upload_routes",
    "app.notas_entrada.consulta_routes",
    "app.comissoes_schemas",
    "app.analise_racoes_schemas",
    "app.analise_racoes_filters",
    "app.conciliacao_aba1_schemas",
    "app.conciliacao_aba1_operacoes_routes",
    "app.produtos.relatorios_validade_routes",
    "app.produtos.relatorios_valorizacao_routes",
]


def _source(relative: str) -> str:
    return (BACKEND_ROOT / relative).read_text(encoding="utf-8")


def _line_count(relative: str) -> int:
    return len(_source(relative).splitlines())


def test_proxima_fatia_backend_sai_da_faixa_acima_de_1000_linhas():
    oversized = {
        relative: _line_count(relative)
        for relative in TARGET_FILES
        if _line_count(relative) > 1000
    }

    assert oversized == {}


def test_modulos_extraidos_da_proxima_fatia_backend_existem():
    for module_name in EXTRACTED_MODULES:
        importlib.import_module(module_name)


def test_routers_principais_incluem_rotas_extraidas():
    notas_source = _source("app/notas_entrada_routes.py")
    conciliacao_source = _source("app/conciliacao_aba1_routes.py")
    produtos_source = _source("app/produtos/relatorios_routes.py")

    assert (
        "from .notas_entrada.upload_routes import router as upload_router"
        in notas_source
    )
    assert (
        "from .notas_entrada.consulta_routes import router as consulta_router"
        in notas_source
    )
    assert "router.include_router(upload_router)" in notas_source
    assert "router.include_router(consulta_router)" in notas_source
    assert (
        "from .conciliacao_aba1_operacoes_routes import router as operacoes_router"
        in conciliacao_source
    )
    assert "router.include_router(operacoes_router)" in conciliacao_source
    assert (
        "from .relatorios_validade_routes import router as validade_router"
        in produtos_source
    )
    assert (
        "from .relatorios_valorizacao_routes import router as valorizacao_router"
        in produtos_source
    )
    assert "router.include_router(validade_router)" in produtos_source
    assert "router.include_router(valorizacao_router)" in produtos_source


def test_modulos_extraidos_tambem_ficam_focados():
    limits = {
        "app/notas_entrada/upload_routes.py": 830,
        "app/notas_entrada/consulta_routes.py": 380,
        "app/comissoes_schemas.py": 120,
        "app/analise_racoes_schemas.py": 90,
        "app/analise_racoes_filters.py": 105,
        "app/conciliacao_aba1_schemas.py": 45,
        "app/conciliacao_aba1_operacoes_routes.py": 320,
        "app/produtos/relatorios_validade_routes.py": 410,
        "app/produtos/relatorios_valorizacao_routes.py": 330,
    }

    oversized = {
        relative: _line_count(relative)
        for relative, max_lines in limits.items()
        if _line_count(relative) > max_lines
    }

    assert oversized == {}
