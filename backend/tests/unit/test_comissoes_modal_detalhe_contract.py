from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = REPO_ROOT / "frontend"


def _frontend_source(relative_path: str) -> str:
    return (FRONTEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_detalhe_comissao_marca_backdrop_e_painel_como_modal_legitimo():
    detalhe = _frontend_source("src/pages/comissoes/ComissaoDetalhe.jsx")

    assert 'data-modal-backdrop-for="comissao-detalhe"' in detalhe
    assert 'data-modal-panel="comissao-detalhe"' in detalhe
    assert 'role="dialog"' in detalhe
    assert 'aria-modal="true"' in detalhe


def test_layout_nao_destrava_backdrop_com_painel_modal_ativo():
    layout = _frontend_source("src/components/Layout.jsx")

    assert 'getAttribute("data-modal-backdrop-for")' in layout
    assert 'querySelectorAll("[data-modal-panel]")' in layout
    assert 'getAttribute("data-modal-panel") === modalBackdropFor' in layout


def test_layout_watchdog_nao_recolhe_sidebar_ao_neutralizar_overlay_automaticamente():
    layout = _frontend_source("src/components/Layout.jsx")

    assert "neutralizarOverlaysOrfaos" in layout
    assert "destravarTela(true)" not in layout
