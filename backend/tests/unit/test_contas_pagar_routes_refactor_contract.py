from pathlib import Path

from app import contas_pagar_routes
from app.financeiro import contas_pagar_recorrencia_routes, contas_pagar_schemas


ROOT = Path(__file__).resolve().parents[2]


def test_contas_pagar_routes_reexports_schemas_and_recorrencia_handlers():
    assert contas_pagar_routes.ContaPagarCreate is contas_pagar_schemas.ContaPagarCreate
    assert contas_pagar_routes.ContaPagarUpdate is contas_pagar_schemas.ContaPagarUpdate
    assert (
        contas_pagar_routes.ContaPagarRecorrenciaBulkDelete
        is contas_pagar_schemas.ContaPagarRecorrenciaBulkDelete
    )
    assert (
        contas_pagar_routes.listar_recorrencia_conta_pagar
        is contas_pagar_recorrencia_routes.listar_recorrencia_conta_pagar
    )
    assert (
        contas_pagar_routes.excluir_recorrencias_contas_pagar
        is contas_pagar_recorrencia_routes.excluir_recorrencias_contas_pagar
    )
    assert (
        contas_pagar_routes.processar_recorrencias_contas_pagar
        is contas_pagar_recorrencia_routes.processar_recorrencias_contas_pagar
    )


def test_recorrencia_routes_are_registered_on_main_router():
    paths = {route.path for route in contas_pagar_routes.router.routes}

    assert "/contas-pagar/{conta_id}/recorrencia" in paths
    assert "/contas-pagar/recorrencias/excluir" in paths
    assert "/contas-pagar/processar-recorrencias" in paths


def test_contas_pagar_routes_stays_below_large_file_threshold_after_extraction():
    routes_source = ROOT / "app" / "contas_pagar_routes.py"
    schemas_source = ROOT / "app" / "financeiro" / "contas_pagar_schemas.py"
    recorrencia_source = (
        ROOT / "app" / "financeiro" / "contas_pagar_recorrencia_routes.py"
    )

    assert len(routes_source.read_text(encoding="utf-8").splitlines()) < 2000
    assert len(schemas_source.read_text(encoding="utf-8").splitlines()) > 140
    assert len(recorrencia_source.read_text(encoding="utf-8").splitlines()) > 220
