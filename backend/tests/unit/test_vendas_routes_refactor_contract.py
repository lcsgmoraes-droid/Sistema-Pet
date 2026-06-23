from pathlib import Path

from app import vendas_routes
from app.vendas import devolucoes_routes, pagamentos_routes, routes_common


ROOT = Path(__file__).resolve().parents[2]


def test_vendas_routes_reexports_extracted_payment_and_return_handlers():
    assert (
        vendas_routes.atualizar_nsu_pagamento
        is pagamentos_routes.atualizar_nsu_pagamento
    )
    assert (
        vendas_routes.listar_pagamentos_venda
        is pagamentos_routes.listar_pagamentos_venda
    )
    assert vendas_routes.excluir_pagamento is pagamentos_routes.excluir_pagamento
    assert vendas_routes.registrar_devolucao is devolucoes_routes.registrar_devolucao


def test_vendas_routes_reexports_common_helpers():
    assert (
        vendas_routes._validar_tenant_e_obter_usuario
        is routes_common._validar_tenant_e_obter_usuario
    )
    assert (
        vendas_routes._normalizar_motivo_exclusao_venda
        is routes_common._normalizar_motivo_exclusao_venda
    )


def test_extracted_routes_are_registered_on_main_router():
    paths = {route.path for route in vendas_routes.router.routes}

    assert "/vendas/{venda_id}/pagamento/{pagamento_id}/nsu" in paths
    assert "/vendas/{venda_id}/pagamentos" in paths
    assert "/vendas/pagamentos/{pagamento_id}" in paths
    assert "/vendas/{venda_id}/devolucao" in paths


def test_vendas_routes_stays_below_large_file_threshold_after_extraction():
    vendas_source = ROOT / "app" / "vendas_routes.py"
    pagamentos_source = ROOT / "app" / "vendas" / "pagamentos_routes.py"
    devolucoes_source = ROOT / "app" / "vendas" / "devolucoes_routes.py"

    assert len(vendas_source.read_text(encoding="utf-8").splitlines()) < 1800
    assert len(pagamentos_source.read_text(encoding="utf-8").splitlines()) > 200
    assert len(devolucoes_source.read_text(encoding="utf-8").splitlines()) > 450
