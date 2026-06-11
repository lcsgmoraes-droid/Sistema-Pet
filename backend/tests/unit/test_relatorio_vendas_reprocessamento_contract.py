from app import dre_plano_contas_models  # noqa: F401
from app import relatorio_vendas_routes


def test_relatorio_vendas_expoe_rota_de_reprocessamento_manual():
    rotas = {
        (route.path, ",".join(sorted(route.methods)))
        for route in relatorio_vendas_routes.router.routes
    }

    assert ("/relatorios/vendas/reprocessar-rentabilidade", "POST") in rotas
