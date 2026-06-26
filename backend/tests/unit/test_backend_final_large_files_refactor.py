from pathlib import Path
import importlib
import os


os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
TARGET_FILES = [
    "app/auth_routes_multitenant.py",
    "app/bling_integration.py",
    "app/conciliacao_routes.py",
    "app/estoque_transferencia_parceiro_routes.py",
    "app/integracao_bling_nf_routes.py",
]


def _source(relative: str) -> str:
    return (BACKEND_ROOT / relative).read_text(encoding="utf-8")


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_ultimos_arquivos_backend_mapeados_saem_da_faixa_acima_de_1000_linhas():
    oversized = {
        relative: _line_count(BACKEND_ROOT / relative)
        for relative in TARGET_FILES
        if _line_count(BACKEND_ROOT / relative) > 1000
    }

    assert oversized == {}


def test_modulos_extraidos_existem_para_ultimos_arquivos_grandes():
    for module_name in [
        "app.auth.auth_multitenant_schemas",
        "app.auth.auth_multitenant_support",
        "app.bling_integration_fiscal",
        "app.integracao_bling_nf_helpers",
        "app.integracao_bling_nf_pedidos",
        "app.conciliacao_abas_routes",
        "app.estoque.transferencia_parceiro_baixa_routes",
    ]:
        importlib.import_module(module_name)


def test_imports_publicos_antigos_continuam_apontando_para_modulos_novos():
    from app import (
        auth_routes_multitenant,
        bling_integration,
        integracao_bling_nf_routes,
    )
    from app.auth import auth_multitenant_schemas
    from app import bling_integration_fiscal, integracao_bling_nf_helpers
    from app import integracao_bling_nf_pedidos

    assert auth_routes_multitenant.LoginRequest is auth_multitenant_schemas.LoginRequest
    assert (
        auth_routes_multitenant.RegisterRequest
        is auth_multitenant_schemas.RegisterRequest
    )
    assert (
        auth_routes_multitenant.LoginResponse is auth_multitenant_schemas.LoginResponse
    )
    assert (
        bling_integration.prevalidar_fiscal_venda
        is bling_integration_fiscal.prevalidar_fiscal_venda
    )
    assert (
        bling_integration.aplicar_correcoes_fiscais_venda
        is bling_integration_fiscal.aplicar_correcoes_fiscais_venda
    )
    assert (
        integracao_bling_nf_routes._nf_webhook_autorizada
        is integracao_bling_nf_helpers._nf_webhook_autorizada
    )
    assert (
        integracao_bling_nf_routes._registrar_nf_no_pedido
        is integracao_bling_nf_pedidos._registrar_nf_no_pedido
    )
    assert (
        integracao_bling_nf_routes._remover_nf_do_pedido
        is integracao_bling_nf_pedidos._remover_nf_do_pedido
    )


def test_router_principal_de_conciliacao_inclui_abas_extraidas():
    source = _source("app/conciliacao_routes.py")

    assert (
        "from .conciliacao_abas_routes import router as conciliacao_abas_router"
        in source
    )
    assert "router.include_router(conciliacao_abas_router)" in source


def test_router_principal_de_transferencia_inclui_baixas_extraidas():
    source = _source("app/estoque_transferencia_parceiro_routes.py")

    assert ".estoque.transferencia_parceiro_baixa_routes" in source
    assert "router as transferencia_parceiro_baixa_router" in source
    assert "router.include_router(transferencia_parceiro_baixa_router)" in source
