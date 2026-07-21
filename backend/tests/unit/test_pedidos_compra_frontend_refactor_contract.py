from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src" / "components"


def _source(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def _line_count(source: str) -> int:
    return len(source.splitlines())


def test_pedidos_compra_publico_orquestra_controller_e_view():
    source = _source("PedidosCompra.jsx")

    assert 'PedidosCompraView from "./compras/PedidosCompraView"' in source
    assert (
        'usePedidosCompraController from "./compras/usePedidosCompraController"'
        in source
    )
    assert "const controller = usePedidosCompraController();" in source
    assert "return <PedidosCompraView controller={controller} />;" in source
    assert _line_count(source) < 80


def test_pedidos_compra_view_agrega_blocos_visuais_extraidos():
    source = _source("compras/PedidosCompraView.jsx")

    assert "PedidoCompraFormulario" in source
    assert "PedidosCompraFiltros" in source
    assert "PedidosCompraTabela" in source
    assert "PedidosCompraModalsLayer" in source
    assert _line_count(source) < 450


def test_pedidos_compra_controller_compose_hooks_e_controladores_focados():
    source = _source("compras/usePedidosCompraController.js")

    for symbol in [
        "usePedidosCompraSugestao",
        "usePedidosCompraGruposFornecedores",
        "createPedidosCompraDataController",
        "createPedidosCompraItemController",
        "createPedidosCompraFormularioController",
        "createPedidosCompraOperacoesController",
    ]:
        assert symbol in source

    assert _line_count(source) < 700


def test_pedidos_compra_modulos_extraidos_ficam_abaixo_de_500_linhas():
    limits = {
        "compras/pedidosCompraDataController.js": 500,
        "compras/pedidosCompraItemController.js": 500,
        "compras/pedidosCompraFormularioController.js": 500,
        "compras/pedidosCompraOperacoesController.js": 500,
    }

    for relative_path, max_lines in limits.items():
        source = _source(relative_path)
        assert _line_count(source) < max_lines, relative_path


def test_pedidos_compra_frontend_preserva_endpoints_criticos():
    data_controller = _source("compras/pedidosCompraDataController.js")
    item_controller = _source("compras/pedidosCompraItemController.js")
    formulario_controller = _source("compras/pedidosCompraFormularioController.js")
    operacoes_controller = _source("compras/pedidosCompraOperacoesController.js")

    assert 'api.get("/pedidos-compra/", { params })' in data_controller
    assert '"/pedidos-compra/envio/status"' in data_controller
    assert "api.get(`/produtos/?${params.toString()}`)" in item_controller
    assert (
        "api.get(`/pedidos-compra/rascunho/fornecedor/${fornecedorId}`"
        in formulario_controller
    )

    for endpoint in [
        'api.post("/pedidos-compra/", dadosEnvio)',
        "`/pedidos-compra/${pedidoParaEnviar}/enviar`",
        "`/pedidos-compra/${id}/confirmar`",
        "`/pedidos-compra/${id}/export/pdf`",
        "`/pedidos-compra/${id}/export/excel`",
        "`/pedidos-compra/${pedido.id}`",
        "`/pedidos-compra/${id}/reverter`",
        "`/pedidos-compra/${pedido.id}/cancelar`",
        "`/pedidos-compra/${pedidoEditando.id}`",
        "`/pedidos-compra/${pedidoSelecionado.id}/receber`",
    ]:
        assert endpoint in operacoes_controller


def test_sugestao_compra_considera_todos_os_produtos_habilitados_do_escopo():
    hook = _source("compras/usePedidosCompraSugestao.jsx")
    header = _source("compras/PedidosCompraSugestaoHeader.jsx")

    assert "apenas_fornecedor_principal" not in hook
    assert "Somente principais do grupo" not in header
    assert "Produtos habilitados de qualquer CNPJ do grupo" in header
    assert "seja o fornecedor principal ou alternativo do produto" in header


def test_listagem_de_pedidos_reduz_acoes_visiveis_e_controla_paginacao():
    filtros = _source("compras/PedidosCompraFiltros.jsx")
    tabela = _source("compras/PedidosCompraTabela.jsx")
    data_controller = _source("compras/pedidosCompraDataController.js")

    assert 'label: "Em andamento"' in filtros
    assert "Mais filtros" in filtros
    assert "PaginationControls" in tabela
    assert "pedidoAcoesAberto" in tabela
    assert "Mais" in tabela
    assert "page_size" in data_controller
    assert "alterarPaginaPedidos" in data_controller
