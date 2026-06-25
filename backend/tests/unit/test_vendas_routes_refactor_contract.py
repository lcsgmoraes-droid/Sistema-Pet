from pathlib import Path

from app import vendas_routes
from app.vendas import (
    cancelamento_routes,
    crud_routes,
    devolucoes_routes,
    entrega_routes,
    finalizacao_routes,
    pagamentos_routes,
    relatorios_routes,
    routes_common,
    status_routes,
)


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


def test_vendas_routes_reexports_extracted_core_handlers():
    assert vendas_routes.listar_vendas is crud_routes.listar_vendas
    assert vendas_routes.buscar_venda is crud_routes.buscar_venda
    assert vendas_routes.criar_venda is crud_routes.criar_venda
    assert vendas_routes.atualizar_venda is crud_routes.atualizar_venda
    assert (
        vendas_routes._resolver_retirado_por_conclusao
        is entrega_routes._resolver_retirado_por_conclusao
    )
    assert vendas_routes.finalizar_venda is finalizacao_routes.finalizar_venda
    assert vendas_routes.cancelar_venda is cancelamento_routes.cancelar_venda
    assert vendas_routes.excluir_venda is cancelamento_routes.excluir_venda
    assert vendas_routes.reabrir_venda is status_routes.reabrir_venda
    assert vendas_routes.relatorio_resumo is relatorios_routes.relatorio_resumo


def test_extracted_routes_are_registered_on_main_router():
    paths = {route.path for route in vendas_routes.router.routes}

    assert "/vendas" in paths
    assert "/vendas/{venda_id}" in paths
    assert "/vendas/{venda_id}/marcar-entregue" in paths
    assert "/vendas/{venda_id}/marcar-pronto-retirada" in paths
    assert "/vendas/{venda_id}/finalizar" in paths
    assert "/vendas/{venda_id}/cancelar" in paths
    assert "/vendas/{venda_id}/reabrir" in paths
    assert "/vendas/{venda_id}/status" in paths
    assert "/vendas/relatorios/resumo" in paths
    assert "/vendas/{venda_id}/pagamento/{pagamento_id}/nsu" in paths
    assert "/vendas/{venda_id}/pagamentos" in paths
    assert "/vendas/pagamentos/{pagamento_id}" in paths
    assert "/vendas/{venda_id}/devolucao" in paths


def test_vendas_routes_stays_below_large_file_threshold_after_extraction():
    vendas_source = ROOT / "app" / "vendas_routes.py"
    pagamentos_source = ROOT / "app" / "vendas" / "pagamentos_routes.py"
    devolucoes_source = ROOT / "app" / "vendas" / "devolucoes_routes.py"
    extracted_sources = [
        ROOT / "app" / "vendas" / "crud_routes.py",
        ROOT / "app" / "vendas" / "entrega_routes.py",
        ROOT / "app" / "vendas" / "finalizacao_routes.py",
        ROOT / "app" / "vendas" / "cancelamento_routes.py",
        ROOT / "app" / "vendas" / "status_routes.py",
        ROOT / "app" / "vendas" / "relatorios_routes.py",
    ]

    assert len(vendas_source.read_text(encoding="utf-8").splitlines()) < 200
    for source in extracted_sources:
        assert len(source.read_text(encoding="utf-8").splitlines()) < 700
    assert len(pagamentos_source.read_text(encoding="utf-8").splitlines()) > 200
    assert len(devolucoes_source.read_text(encoding="utf-8").splitlines()) > 450
