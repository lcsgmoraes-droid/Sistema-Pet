from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_editor_produto_libera_formulario_antes_dos_complementos_e_permite_retry():
    hook = _source("frontend/src/hooks/useProdutosNovoCarregamento.js")
    pagina = _source("frontend/src/pages/ProdutosNovo.jsx")
    carregar = hook.split("const carregarProduto = async () => {", 1)[1].split(
        "const carregarProdutoParaClone", 1
    )[0]

    assert carregar.index("setLoading(false)") < carregar.index(
        "const resultadosComplementares = await Promise.allSettled"
    )
    assert "produtoRequestRef" in hook
    assert "requestAindaAtiva" in carregar
    assert "erroCarregamento" in pagina
    assert "Tentar novamente" in pagina


def test_editor_e_balanco_nao_recarregam_catalogos_a_cada_produto_ou_pagina():
    editor = _source("frontend/src/hooks/useProdutosNovoCarregamento.js")
    balanco = _source("frontend/src/hooks/useProdutosBalancoPage.js")

    assert "useEffect(() => {\n    carregarDadosAuxiliares();\n  }, []);" in editor
    carregar_balanco = balanco.split(
        "const carregarDadosComFiltros = async", 1
    )[1].split("const carregarCatalogos", 1)[0]
    assert "getProdutos(params)" in carregar_balanco
    assert "getMarcas()" not in carregar_balanco
    assert 'api.get("/clientes/"' not in carregar_balanco


def test_contas_receber_busca_relacoes_em_lote_e_frontend_nao_bloqueia_auxiliares():
    backend = _source("backend/app/contas_receber_consulta_routes.py")
    frontend = _source("frontend/src/components/ContasReceber.jsx")
    listar = backend.split("def listar_contas_receber(", 1)[1].split(
        "# ============================================================================", 1
    )[0]
    serializacao = listar.split("for conta in contas:", 1)[1]
    carregar_principal = frontend.split("const carregarDados = async () => {", 1)[
        1
    ].split("const carregarContasComFiltros", 1)[0]

    assert "clientes_por_id" in listar
    assert "numeros_venda_por_id" in listar
    assert "db.query(Cliente)" not in serializacao
    assert "db.query(Venda)" not in serializacao
    assert "/contas-receber/" in carregar_principal
    assert "/clientes/" not in carregar_principal
    assert "carregarDadosAuxiliares();" in frontend


def test_fluxo_caixa_resolve_vendas_em_lote_e_valor_empresa_limita_colunas():
    fluxo = _source("backend/app/financeiro/fluxo_caixa_routes.py")
    valor_empresa = _source("backend/app/financeiro/valor_empresa_service.py")

    assert "def _mapa_numeros_venda_por_conta" in fluxo
    assert "numeros_venda_por_conta.get" in fluxo
    assert "joinedload(ContaPagar.fornecedor)" in fluxo
    assert "joinedload(ContaReceber.cliente)" in fluxo
    assert "load_only(" in valor_empresa
    assert "query.with_entities(" in valor_empresa
