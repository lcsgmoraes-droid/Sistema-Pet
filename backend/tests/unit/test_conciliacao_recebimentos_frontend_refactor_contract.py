from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _line_count(path: str) -> int:
    return len(_source(path).splitlines())


def test_aba2_conciliacao_recebimentos_separa_fluxo_da_view():
    page_source = _source("frontend/src/pages/Aba2ConciliacaoRecebimentos.jsx")
    view_source = _source(
        "frontend/src/pages/conciliacaoRecebimentos/Aba2ConciliacaoRecebimentosView.jsx"
    )

    assert (
        'import Aba2ConciliacaoRecebimentosView from "./conciliacaoRecebimentos/Aba2ConciliacaoRecebimentosView";'
        in page_source
    )
    assert 'api.post("/conciliacao/aba2/validar-recebimentos"' in page_source
    assert "useNavigate" not in page_source

    assert 'import { useNavigate } from "react-router-dom";' in view_source
    assert "Validar Cascata (3 arquivos)" in view_source
    assert "mostrarModalConfirmacao" in view_source
    assert "mostrarModalDivergencia" in view_source


def test_aba2_conciliacao_recebimentos_fica_abaixo_dos_limites_grandes():
    assert _line_count("frontend/src/pages/Aba2ConciliacaoRecebimentos.jsx") < 700
    assert (
        _line_count(
            "frontend/src/pages/conciliacaoRecebimentos/Aba2ConciliacaoRecebimentosView.jsx"
        )
        < 1000
    )
