from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_opening_conference_without_divergences_keeps_all_items_visible():
    source = read_source("frontend/src/components/EntradaXML.jsx")

    assert (
        "setFiltroItensNota(temDivergenciaConferencia ? 'divergencias' : 'todos')"
        in source
    )
    assert (
        "setFiltroItensNota((abrirConferencia || temDivergenciaConferencia) ? 'divergencias' : 'todos')"
        not in source
    )


def test_empty_divergence_filter_falls_back_to_all_invoice_items():
    source = read_source(
        "frontend/src/components/entrada-xml/useEntradaXmlConferencia.js"
    )

    assert "itensComDivergenciaDetalhe.length > 0" in source
    assert (
        "const itensExibidosNota = filtroItensNota === 'divergencias'\n"
        "    ? itensComDivergenciaDetalhe\n"
        "    : itensNotaDetalhe;"
    ) not in source
