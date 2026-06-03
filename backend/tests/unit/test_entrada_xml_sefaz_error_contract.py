from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_entrada_xml_sefaz_normaliza_erro_cloudflare_no_frontend():
    source = (REPO_ROOT / "frontend/src/components/entrada-xml/useEntradaXmlSefaz.js").read_text(
        encoding="utf-8"
    )

    assert "normalizarMensagemErroSefaz" in source
    assert "origin web server" in source
    assert "Cloudflare" in source
    assert "SEFAZ esta temporariamente indisponivel" in source
    assert "setErroSefaz(normalizarMensagemErroSefaz(err))" in source
