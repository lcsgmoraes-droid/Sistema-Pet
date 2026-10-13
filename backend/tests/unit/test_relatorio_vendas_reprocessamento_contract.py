from fastapi import FastAPI

from app import dre_plano_contas_models  # noqa: F401
from app import relatorio_vendas_routes


def test_relatorio_vendas_expoe_rota_de_reprocessamento_manual():
    # O grafo interno pode conter inclusões lazy de outros routers, sem path.
    # OpenAPI verifica o contrato público depois de resolver todas as inclusões.
    app = FastAPI()
    app.include_router(relatorio_vendas_routes.router)
    operations = app.openapi()["paths"]["/relatorios/vendas/reprocessar-rentabilidade"]
    assert "post" in operations
    assert operations["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ReprocessarRentabilidadeVendasResponse")
