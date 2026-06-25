from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src" / "pages"


def _source(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def _line_count(source: str) -> int:
    return len(source.splitlines())


def test_central_nf_saida_controller_fica_abaixo_do_limite_critico():
    source = _source("CentralNFSaida.jsx")

    assert "CentralNFSaidaView" in source
    assert "api.get(`/nfe/?${params.toString()}`)" in source
    assert 'api.get("/sefaz/config")' in source
    assert 'api.post("/sefaz/consultar"' in source
    assert "reconciliar-fluxo" in source
    assert _line_count(source) < 500


def test_central_nf_saida_view_agrega_paineis_extraidos():
    source = _source("centralNFSaida/CentralNFSaidaView.jsx")

    assert "SefazToolsPanel" in source
    assert "SefazConsultasSessao" in source
    assert "NFSaidaFilters" in source
    assert "NFSaidaList" in source
    assert "NFSaidaDetalhesModal" in source
    assert "NFSaidaCancelamentoModal" in source
    assert _line_count(source) < 250


def test_central_nf_saida_componentes_extraidos_ficam_menores_que_700_linhas():
    arquivos = [
        "centralNFSaida/CentralNFSaidaHeader.jsx",
        "centralNFSaida/centralNFSaidaUtils.jsx",
        "centralNFSaida/CentralNFSaidaView.jsx",
        "centralNFSaida/NFSaidaCancelamentoModal.jsx",
        "centralNFSaida/NFSaidaDetalhesModal.jsx",
        "centralNFSaida/NFSaidaFilters.jsx",
        "centralNFSaida/NFSaidaList.jsx",
        "centralNFSaida/SefazConsultasSessao.jsx",
        "centralNFSaida/SefazToolsPanel.jsx",
    ]

    for arquivo in arquivos:
        assert _line_count(_source(arquivo)) < 700, arquivo


def test_central_nf_saida_preserva_marcadores_visuais_e_acoes_principais():
    lista = _source("centralNFSaida/NFSaidaList.jsx")
    detalhes = _source("centralNFSaida/NFSaidaDetalhesModal.jsx")
    sefaz = _source("centralNFSaida/SefazToolsPanel.jsx")
    cancelamento = _source("centralNFSaida/NFSaidaCancelamentoModal.jsx")

    assert "Baixar DANFE" in detalhes
    assert "Baixar XML" in detalhes
    assert "Forçar reconciliação desta NF" in lista
    assert "Rotina automática de sincronização" in sefaz
    assert "Cancelar Nota Fiscal" in cancelamento
