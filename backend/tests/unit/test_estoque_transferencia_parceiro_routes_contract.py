from pathlib import Path
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_transferencia_parceiro_routes


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_transferencia_parceiro_routes_ficam_em_router_dedicado():
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in estoque_transferencia_parceiro_routes.router.routes
    }

    assert ("/estoque/transferencia-parceiro", "POST") in routes
    assert ("/estoque/transferencia-parceiro/{conta_receber_id}", "PUT") in routes
    assert ("/estoque/transferencia-parceiro/historico", "GET") in routes
    assert ("/estoque/transferencia-parceiro/{conta_receber_id}/pdf", "GET") in routes
    assert ("/estoque/transferencia-parceiro/pdf-consolidado", "POST") in routes
    assert (
        "/estoque/transferencia-parceiro/{conta_receber_id}/enviar-email",
        "POST",
    ) in routes
    assert (
        "/estoque/transferencia-parceiro/{conta_receber_id}/contas-pagar-compensacao",
        "GET",
    ) in routes
    assert (
        "/estoque/transferencia-parceiro/{conta_receber_id}/receber",
        "POST",
    ) in routes
    assert ("/estoque/transferencia-parceiro/{conta_receber_id}", "DELETE") in routes


def test_estoque_routes_nao_expõe_mais_decorators_de_transferencia_parceiro():
    source = _source("app/estoque_routes.py")

    assert '"/transferencia-parceiro' not in source
    assert "class TransferenciaParceiroRequest" not in source
    assert "def transferir_estoque_para_parceiro(" not in source
    assert "def editar_transferencia_parceiro(" not in source
    assert "def excluir_transferencia_parceiro(" not in source


def test_main_registra_router_de_transferencia_parceiro():
    main_source = _source("app/main.py")

    assert "from app.estoque_transferencia_parceiro_routes import" in main_source
    assert "router as estoque_transferencia_parceiro_router" in main_source
    assert "app.include_router(" in main_source
    assert "estoque_transferencia_parceiro_router" in main_source
    assert 'tags=["Estoque - Transferencia Parceiro"]' in main_source


def test_transferencia_parceiro_centraliza_formato_de_data_curta():
    source = _source("app/estoque_transferencia_parceiro_routes.py")

    assert "_FORMATO_DATA_CURTA" in source
    assert source.count("%d/%m/%Y") == 1
