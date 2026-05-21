import inspect
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_validade_routes


def test_validade_routes_expose_processing_actions_and_report():
    routes = {(route.path, ",".join(sorted(route.methods))) for route in estoque_validade_routes.router.routes}

    assert ("/estoque/validade/processar", "POST") in routes
    assert ("/estoque/validade/pendencias", "GET") in routes
    assert ("/estoque/validade/{bloqueio_id}/descartar", "POST") in routes
    assert ("/estoque/validade/{bloqueio_id}/trocar-fornecedor", "POST") in routes
    assert ("/estoque/validade/{bloqueio_id}/retornar-vendavel", "POST") in routes
    assert ("/estoque/validade/pdv-alertas", "GET") in routes
    assert ("/estoque/validade/relatorio-perdas", "GET") in routes


def test_validade_routes_use_selected_tenant_context():
    source = inspect.getsource(estoque_validade_routes)

    assert "Depends(get_current_user_and_tenant)" in source
    assert "tenant_id" in source
    assert "Depends(get_current_user)" not in source
