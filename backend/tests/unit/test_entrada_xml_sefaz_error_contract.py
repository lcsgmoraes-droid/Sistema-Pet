from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_entrada_xml_sefaz_normaliza_erro_cloudflare_no_frontend():
    hook_source = (
        REPO_ROOT / "frontend/src/components/entrada-xml/useEntradaXmlSefaz.js"
    ).read_text(encoding="utf-8")
    source = (
        REPO_ROOT / "frontend/src/components/entrada-xml/sefazConsultaUtils.mjs"
    ).read_text(encoding="utf-8")

    assert "normalizarMensagemErroSefaz(err)" in hook_source
    assert "origin web server" in source
    assert "Cloudflare" in source
    assert "SEFAZ está temporariamente indisponível" in source
    assert "setErroSefaz(msg)" in hook_source


def test_entrada_xml_bloqueia_consulta_e_exibe_pendencias_de_configuracao():
    hook_source = (
        REPO_ROOT / "frontend/src/components/entrada-xml/useEntradaXmlSefaz.js"
    ).read_text(encoding="utf-8")
    panel_source = (
        REPO_ROOT / "frontend/src/components/entrada-xml/EntradaXmlSefazPanels.jsx"
    ).read_text(encoding="utf-8")

    assert (
        "pendencias: Array.isArray(data.pendencias) ? data.pendencias : []"
        in hook_source
    )
    assert 'cfgSefaz.modo === "real" && cfgSefaz.cert_ok' in hook_source
    assert "carregarConfigSefaz();" in hook_source
    assert "Consulta bloqueada: configuração SEFAZ incompleta." in panel_source
    assert "Configurar certificado e integração SEFAZ" in panel_source
    assert "!configuracaoSefazPronta" in panel_source
