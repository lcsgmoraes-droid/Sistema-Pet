from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_dre_usa_mesmo_criterio_de_status_da_tela_de_vendas():
    source = _source("backend/app/dre_canais_routes.py")

    assert "def _filtro_status_venda_dre" in source
    assert 'Venda.status != "cancelada"' in source
    assert "Venda.status.in_" not in source


def test_dre_abre_com_todos_os_canais_por_padrao():
    backend = _source("backend/app/dre_canais_routes.py")
    frontend = _source("frontend/src/components/DRE.jsx")

    assert 'canais: str = Query("",' in backend
    assert "CANAIS_DRE_PADRAO.map((canal) => canal.id)" in frontend
