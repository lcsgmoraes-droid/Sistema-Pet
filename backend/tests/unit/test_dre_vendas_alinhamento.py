from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_dre_usa_mesmo_criterio_de_status_da_tela_de_vendas():
    source = _source("backend/app/dre_canais/base.py")

    assert "def _filtro_status_venda_dre" in source
    assert 'Venda.status != "cancelada"' in source
    assert "Venda.status.in_" not in source


def test_dre_abre_somente_com_loja_fisica_por_padrao():
    backend = _source("backend/app/dre_canais/routes.py")
    frontend = _source("frontend/src/components/DRE.jsx")

    assert "canais: str = Query(" in backend
    assert '        "",' in backend
    assert 'canais_selecionados = ["loja_fisica"]' in backend
    assert 'useState(["loja_fisica"])' in frontend
    assert "CANAIS_DRE_PADRAO.map((canal) => canal.id)" not in frontend
