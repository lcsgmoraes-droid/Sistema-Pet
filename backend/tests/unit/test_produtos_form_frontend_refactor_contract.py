from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(*parts: str) -> str:
    return (REPO_ROOT / Path(*parts)).read_text(encoding="utf-8")


def _line_count(*parts: str) -> int:
    return len(_read(*parts).splitlines())


def test_produtos_form_page_is_a_thin_shell_after_refactor():
    source = _read("frontend", "src", "pages", "ProdutosForm.jsx")

    assert _line_count("frontend", "src", "pages", "ProdutosForm.jsx") < 100
    assert "useProdutosFormController" in source
    assert "ProdutosFormView" in source
    assert "useState" not in source
    assert "useEffect" not in source
    assert 'from "../api/produtos"' not in source


def test_produtos_form_refactor_modules_are_present_and_focused():
    expected_limits = {
        "useProdutosFormController.js": 450,
        "ProdutosFormView.jsx": 180,
        "ProdutosFormDadosTab.jsx": 650,
        "ProdutosFormImagensTab.jsx": 180,
        "ProdutosFormFornecedoresTab.jsx": 220,
        "ProdutosFormLotesTab.jsx": 180,
        "ProdutosFormVariacoesTab.jsx": 240,
        "ProdutosFormModals.jsx": 120,
    }

    base = Path("frontend", "src", "pages", "produtos", "form")
    for filename, limit in expected_limits.items():
        path = base / filename
        assert (REPO_ROOT / path).exists(), f"{path.as_posix()} nao existe"
        assert _line_count(*path.parts) < limit, (
            f"{path.as_posix()} ficou grande demais"
        )


def test_produtos_form_controller_preserves_backend_contracts():
    source = _read(
        "frontend",
        "src",
        "pages",
        "produtos",
        "form",
        "useProdutosFormController.js",
    )

    required_tokens = [
        "getProduto(id)",
        "createProduto(dados)",
        "updateProduto(id, dados)",
        "getCategorias({ apenas_ativas: true })",
        "getMarcas({ apenas_ativas: true })",
        "getDepartamentos({ apenas_ativos: true })",
        'api.get("/clientes/"',
        "getFornecedoresProduto(id)",
        "getLotes(id)",
        "gerarSKU()",
        "uploadImagemProduto(id, formData)",
        "deleteImagemProduto(imagemId)",
        "api.put(`/produtos/imagens/${imagemId}`",
        "addFornecedorProduto(id, dados)",
        "updateFornecedorProduto(fornecedorEdit.id, dados)",
        "deleteFornecedorProduto(fornecedorId)",
        "entradaEstoque(id, dados)",
        "saidaFIFO(id, dados)",
        "api.get(`/produtos/${id}/variacoes`)",
    ]

    for token in required_tokens:
        assert token in source


def test_produtos_form_tabs_keep_expected_user_flows():
    tabs = {
        "ProdutosFormDadosTab.jsx": [
            "SKU",
            "Nome do Produto",
            "Canal",
            "Controlar por Lotes",
            "Cadastrar",
        ],
        "ProdutosFormImagensTab.jsx": [
            "Imagens do Produto",
            "Adicionar Imagem",
            "Principal",
            "Excluir",
        ],
        "ProdutosFormFornecedoresTab.jsx": [
            "Fornecedores do Produto",
            "Adicionar Fornecedor",
            "FornecedorIdentity",
            "formatarMoeda",
        ],
        "ProdutosFormLotesTab.jsx": [
            "Controle de Lotes",
            "Entrada",
            "FIFO",
            "formatarData",
        ],
        "ProdutosFormVariacoesTab.jsx": [
            "Produto",
            "Nova",
            "Carregando",
            "formatarMoeda",
        ],
    }

    base = Path("frontend", "src", "pages", "produtos", "form")
    for filename, tokens in tabs.items():
        source = _read(*(base / filename).parts)
        for token in tokens:
            assert token in source
