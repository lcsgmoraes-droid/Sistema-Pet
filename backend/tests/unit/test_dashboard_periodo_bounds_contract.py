from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import app.dashboard_routes as dashboard_routes
from app.dashboard_routes import _intervalo_dias_calendario


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_ROUTES = BACKEND_ROOT / "app" / "dashboard_routes.py"


def _function_source(source: str, function_name: str) -> str:
    start = source.index(f"async def {function_name}(")
    next_route = source.find("\n@router.", start + 1)
    if next_route == -1:
        return source[start:]
    return source[start:next_route]


def test_dashboard_periodo_dias_query_params_are_bounded_before_range_loops():
    source = DASHBOARD_ROUTES.read_text(encoding="utf-8")

    for function_name in [
        "obter_entradas_saidas_por_dia",
        "obter_vendas_por_dia",
    ]:
        function_source = _function_source(source, function_name)
        assert "periodo_dias: int = Query(30, ge=0, le=366)" in function_source


def test_dashboard_hoje_usa_dia_civil_de_brasilia():
    inicio, fim = _intervalo_dias_calendario(1, datetime(2026, 7, 16, 13, 27))

    assert inicio == datetime(2026, 7, 16, 0, 0)
    assert fim == datetime(2026, 7, 17, 0, 0)


def test_dashboard_sete_dias_inclui_hoje_e_seis_dias_anteriores():
    inicio, fim = _intervalo_dias_calendario(7, datetime(2026, 7, 16, 13, 27))

    assert inicio == datetime(2026, 7, 10, 0, 0)
    assert fim == datetime(2026, 7, 17, 0, 0)


def test_dashboard_classifica_vencimento_pelo_dia_civil_sem_considerar_hora():
    classificar = getattr(
        dashboard_routes, "_classificar_data_vencimento_dashboard", None
    )

    assert callable(classificar), "dashboard precisa de uma regra unica por data"
    hoje = date(2026, 8, 13)
    assert classificar(date(2026, 8, 12), hoje) == "vencido"
    assert classificar(date(2026, 8, 13), hoje) == "vence_hoje"
    assert classificar(date(2026, 8, 14), hoje) == "a_vencer"


def test_resumo_dashboard_separa_vencidas_das_contas_que_vencem_hoje():
    source = DASHBOARD_ROUTES.read_text(encoding="utf-8")
    function_source = _function_source(source, "obter_resumo_dashboard")

    assert function_source.count("data_vencimento < hoje") >= 2
    assert function_source.count("data_vencimento == hoje") >= 2


def test_lista_de_contas_vencidas_tambem_usa_brasilia_e_exclui_hoje():
    source = DASHBOARD_ROUTES.read_text(encoding="utf-8")
    function_source = _function_source(source, "obter_contas_vencidas")

    assert "hoje = now_brasilia().date()" in function_source
    assert function_source.count("data_vencimento < hoje") >= 2
    assert "data_vencimento <= hoje" not in function_source
