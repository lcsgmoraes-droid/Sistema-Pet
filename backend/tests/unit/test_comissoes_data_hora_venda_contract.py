from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_demonstrativo_comissoes_retorna_data_hora_real_da_venda():
    fonte = _source("backend/app/comissoes_demonstrativo_routes.py")

    assert "COALESCE(v.data_finalizacao, v.data_venda, ci.data_venda) as data_venda" in fonte
    assert "AND ci.data_venda >= :data_inicio" in fonte
    assert "AND ci.data_venda <= :data_fim" in fonte
    assert "ORDER BY COALESCE(v.data_finalizacao, v.data_venda, ci.data_venda) DESC" in fonte


def test_detalhe_comissao_retorna_data_hora_real_da_venda():
    fonte = _source("backend/app/comissoes_demonstrativo_routes.py")

    assert "COALESCE(v.data_finalizacao, v.data_venda, ci.data_venda) as data_venda," in fonte
