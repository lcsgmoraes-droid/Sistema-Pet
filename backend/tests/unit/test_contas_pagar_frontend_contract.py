from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_contas_pagar_tem_atalhos_de_periodo():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(encoding="utf-8")

    assert "PERIODOS_RAPIDOS_CONTAS_PAGAR" in source
    assert "Hoje" in source
    assert "Amanha" in source
    assert "Semana" in source
    assert "Mes" in source
    assert "calcularIntervaloPeriodoRapido" in source
    assert "aplicarPeriodoRapido" in source
    assert "periodo_rapido" in source
    assert "filtros.periodo_rapido === periodo.value" in source
