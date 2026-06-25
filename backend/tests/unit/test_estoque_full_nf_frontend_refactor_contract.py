from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(*parts: str) -> str:
    return (REPO_ROOT / Path(*parts)).read_text(encoding="utf-8")


def _line_count(*parts: str) -> int:
    return len(_read(*parts).splitlines())


def test_estoque_full_nf_page_is_a_thin_shell_after_refactor():
    source = _read("frontend", "src", "pages", "EstoqueFullNF.jsx")

    assert _line_count("frontend", "src", "pages", "EstoqueFullNF.jsx") < 80
    assert "useEstoqueFullNFController" in source
    assert "EstoqueFullNFView" in source
    assert "useState" not in source
    assert "useEffect" not in source
    assert "api." not in source


def test_estoque_full_nf_modules_are_present_and_focused():
    expected_limits = {
        "useEstoqueFullNFController.js": 700,
        "estoqueFullNFUtils.js": 180,
        "EstoqueFullNFView.jsx": 180,
        "EstoqueFullNFLancamentoPanel.jsx": 460,
        "EstoqueFullNFHistoricoPanel.jsx": 240,
        "EstoqueFullNFModals.jsx": 420,
    }

    base = Path("frontend", "src", "pages", "estoqueFullNF")
    for filename, limit in expected_limits.items():
        path = base / filename
        assert (REPO_ROOT / path).exists(), f"{path.as_posix()} nao existe"
        assert _line_count(*path.parts) < limit, (
            f"{path.as_posix()} ficou grande demais"
        )


def test_estoque_full_nf_controller_preserves_backend_contracts():
    source = _read(
        "frontend",
        "src",
        "pages",
        "estoqueFullNF",
        "useEstoqueFullNFController.js",
    )

    required_tokens = [
        'api.get("/categorias-financeiras?tipo=despesa")',
        'api.get("/estoque/saida-full-nf/historico?limit=200")',
        'api.get("/dre/categorias")',
        'api.get("/dre/subcategorias")',
        'api.post("/estoque/saida-full-xml/parse"',
        'api.post("/estoque/saida-full-nf/validar-estoque"',
        'api.post("/estoque/saida-full-nf"',
        "/estoque/saida-full-nf/${encodeURIComponent(lancamento.numero_nf)}/canal",
        "api.put(`/categorias-financeiras/${categoria.id}`",
        "permitir_estoque_negativo",
        "dre_subcategoria_tarifa_id",
    ]

    for token in required_tokens:
        assert token in source


def test_estoque_full_nf_components_keep_expected_flows():
    expected_tokens = {
        "EstoqueFullNFLancamentoPanel.jsx": [
            "Numero da NF",
            "Canal / origem",
            "Ler XML e preencher",
            "Estoque insuficiente",
            "Tarifa de envio",
            "Confirmar baixa por NF",
        ],
        "EstoqueFullNFHistoricoPanel.jsx": [
            "Historico de baixas FULL",
            "Atualizar historico",
            "Editar canal",
            "Ver itens da baixa",
            "DataTable",
        ],
        "EstoqueFullNFModals.jsx": [
            "Baixa por NF finalizada",
            "Corrigir canal",
            "Editar loja/canal da NF",
            "Vincular categoria a DRE",
            "Vincular e continuar",
        ],
    }

    base = Path("frontend", "src", "pages", "estoqueFullNF")
    for filename, tokens in expected_tokens.items():
        source = _read(*(base / filename).parts)
        for token in tokens:
            assert token in source
