from __future__ import annotations

from datetime import datetime
from pathlib import Path

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
