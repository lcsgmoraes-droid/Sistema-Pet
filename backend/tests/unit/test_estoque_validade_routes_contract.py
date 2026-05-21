import inspect
import os
from datetime import datetime, timezone
from types import SimpleNamespace

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


def test_serializacao_de_validade_expoe_campos_para_relatorio_de_perdas():
    item = SimpleNamespace(
        id=1,
        produto_id=10,
        produto=SimpleNamespace(nome="Defenza"),
        lote_id=20,
        lote=SimpleNamespace(nome_lote="Lote A"),
        status="descartado",
        decisao="descartado",
        origem="rotina",
        data_validade=datetime(2026, 5, 30, tzinfo=timezone.utc),
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        decidido_em=datetime(2026, 5, 21, tzinfo=timezone.utc),
        quantidade_bloqueada=2,
        quantidade_resolvida=2,
        custo_unitario=10,
        custo_total_estimado=20,
        observacao="Produto vencido",
    )

    dados = estoque_validade_routes._serializar(item)

    assert dados["origem"] == "rotina"
    assert dados["created_at"] == "2026-05-20T00:00:00+00:00"
    assert dados["decidido_em"] == "2026-05-21T00:00:00+00:00"
    assert dados["custo_total_estimado"] == 20


def test_relatorio_perdas_filtra_descartados_por_padrao():
    source = inspect.getsource(estoque_validade_routes.relatorio_perdas)

    assert 'EstoqueValidadeBloqueio.status == "descartado"' in source
