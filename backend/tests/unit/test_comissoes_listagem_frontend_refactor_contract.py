from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMISSOES = ROOT / "frontend" / "src" / "pages" / "comissoes"


def _source(relative_path: str) -> str:
    return (COMISSOES / relative_path).read_text(encoding="utf-8")


def _line_count(source: str) -> int:
    return len(source.splitlines())


def test_comissoes_listagem_publico_orquestra_controller_e_view():
    source = _source("ComissoesListagem.jsx")

    assert 'ComissoesListagemView from "./listagem/ComissoesListagemView"' in source
    assert (
        'useComissoesListagemController from "./listagem/useComissoesListagemController"'
        in source
    )
    assert "const controller = useComissoesListagemController();" in source
    assert "return <ComissoesListagemView controller={controller} />;" in source
    assert _line_count(source) < 80


def test_comissoes_listagem_view_agrega_componentes_extraidos():
    source = _source("listagem/ComissoesListagemView.jsx")

    for symbol in [
        "ComissoesListagemResumo",
        "ComissoesListagemFiltros",
        "ComissoesListagemTabela",
        "ComissoesListagemFechamentoModal",
        "ComissaoDetalhe",
    ]:
        assert symbol in source

    assert _line_count(source) < 450


def test_comissoes_listagem_hook_preserva_fluxos_de_api():
    source = _source("listagem/useComissoesListagemController.js")

    for endpoint in [
        '"/comissoes"',
        "`/comissoes/resumo?funcionario_id=${FUNCIONARIO_ID}`",
        '"/comissoes/funcionarios"',
        '"/produtos/"',
        '"/categorias-financeiras"',
        '"/comissoes/formas-pagamento"',
        '"/contas-bancarias"',
        '"/comissoes/fechar"',
        "`/comissoes/fechar-com-pagamento?${params.toString()}`",
    ]:
        assert endpoint in source

    assert _line_count(source) < 700


def test_comissoes_listagem_componentes_extraidos_ficam_focados():
    limits = {
        "listagem/ComissoesListagemResumo.jsx": 220,
        "listagem/ComissoesListagemFiltros.jsx": 420,
        "listagem/ComissoesListagemTabela.jsx": 520,
        "listagem/ComissoesListagemFechamentoModal.jsx": 360,
    }

    for relative_path, max_lines in limits.items():
        source = _source(relative_path)
        assert _line_count(source) < max_lines, relative_path
