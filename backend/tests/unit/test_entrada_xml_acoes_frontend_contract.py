from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_entrada_xml_footer_forca_revisao_de_acoes_antes_de_processar():
    source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlDetalhesFooter.jsx"
    )

    assert "Revisar acoes e processar" in source
    assert "Processar Nota" not in source
    assert "processarNota" not in source
    assert "carregarPreviewProcessamento(notaSelecionada.id)" in source


def test_acoes_processamento_aparecem_antes_da_lista_de_itens():
    source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlRevisaoPrecosModal.jsx"
    )

    assert source.index("Acoes ao processar") < source.index("{itensFiltrados")


def test_processar_nf_abre_confirmacao_final_com_acoes_visiveis():
    source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlRevisaoPrecosModal.jsx"
    )

    assert "Confirmacao final do processamento" in source
    assert "setMostrarConfirmacaoProcessamento(true)" in source
    assert "Processar NF agora" in source
    assert "onClick={confirmarProcessamento}" in source


def test_nota_processada_pode_abrir_lancamento_de_movimentos_pendentes():
    table_source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlNotasTable.jsx"
    )
    modal_source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlVisualizacaoNotaModal.jsx"
    )

    assert "Lancar movimentos" in table_source
    assert "Lancar movimentos pendentes" in modal_source
    assert "carregarPreviewProcessamento(nota.id)" in table_source


def test_entrada_xml_lista_tem_filtros_operacionais_de_nf():
    table_source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlNotasTable.jsx"
    )

    assert "filtrosNotas" in table_source
    assert "onFiltrosChange" in table_source
    assert "Fornecedor" in table_source
    assert "NF ou chave" in table_source
    assert "Data inicial" in table_source
    assert "Data final" in table_source
    assert "Conferencia" in table_source
    assert "limparFiltrosNotas" in table_source
    assert "nota.fornecedor_nome" in table_source
    assert "nota.numero_nota" in table_source
    assert "nota.chave_acesso" in table_source


def test_entrada_xml_usa_paginacao_e_filtros_no_servidor():
    page_source = read_source("frontend/src/components/EntradaXML.jsx")
    table_source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlNotasTable.jsx"
    )
    metricas_source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlMetricas.jsx"
    )

    assert 'useState("pendente")' in page_source
    assert 'api.get("/notas-entrada/listagem"' in page_source
    assert "page_size: 20" in page_source
    assert "PaginationControls" in table_source
    assert "onItemsPerPageChange" in table_source
    assert "totalItems={paginacao.total}" in table_source
    assert "metricas.total_notas" in metricas_source
    assert "metricas.valor_conciliado" in metricas_source


def test_acoes_ja_lancadas_ficam_bloqueadas_na_revisao():
    source = read_source(
        "frontend/src/components/entrada-xml/EntradaXmlRevisaoPrecosModal.jsx"
    )

    assert "acoes_processamento_realizadas" in source
    assert "Ja lancado" in source
    assert "disabled={loading || acaoJaRealizada}" in source
