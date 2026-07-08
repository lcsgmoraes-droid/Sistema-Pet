from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_fluxo_caixa_frontend_tem_preset_proximos_12_meses_mensal():
    source = read_repo("frontend/src/components/FluxoCaixa.jsx")

    assert "proximos_12_meses" in source
    assert "Proximos 12 meses" in source
    assert 'preset === "proximos_12_meses" ? "mes" : filtros.agrupamento' in source
