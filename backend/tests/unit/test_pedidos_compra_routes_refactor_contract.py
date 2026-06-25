from pathlib import Path

from app import pedidos_compra_routes
from app.pedidos_compra import core_routes
from app.pedidos_compra import envio_routes
from app.pedidos_compra import exportacao_routes
from app.pedidos_compra import recebimento_routes
from app.pedidos_compra import schemas
from app.pedidos_compra import sugestao_routes


BACKEND_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PUBLIC_PATHS = {
    "/pedidos-compra/",
    "/pedidos-compra/envio/status",
    "/pedidos-compra/rascunho/fornecedor/{fornecedor_id}",
    "/pedidos-compra/{pedido_id}",
    "/pedidos-compra/{pedido_id}/enviar",
    "/pedidos-compra/{pedido_id}/confirmar",
    "/pedidos-compra/{pedido_id}/cancelar",
    "/pedidos-compra/{pedido_id}/receber",
    "/pedidos-compra/{pedido_id}/export/excel",
    "/pedidos-compra/{pedido_id}/export/pdf",
    "/pedidos-compra/{pedido_id}/reverter",
    "/pedidos-compra/sugestao/{fornecedor_id}",
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def _line_count(relative_path: str) -> int:
    return sum(1 for _ in (BACKEND_ROOT / relative_path).open(encoding="utf-8"))


def test_pedidos_compra_routes_preserva_paths_publicos():
    assert EXPECTED_PUBLIC_PATHS.issubset(_route_paths(pedidos_compra_routes.router))


def test_pedidos_compra_routes_mantem_reexports_compativeis():
    assert pedidos_compra_routes.PedidoCompraRequest is schemas.PedidoCompraRequest
    assert (
        pedidos_compra_routes.PedidoCompraEnviarRequest
        is schemas.PedidoCompraEnviarRequest
    )
    assert (
        pedidos_compra_routes.RecebimentoPedidoRequest
        is schemas.RecebimentoPedidoRequest
    )
    assert pedidos_compra_routes.listar_pedidos is core_routes.listar_pedidos
    assert pedidos_compra_routes.criar_pedido is core_routes.criar_pedido
    assert pedidos_compra_routes.enviar_pedido is envio_routes.enviar_pedido
    assert pedidos_compra_routes.receber_pedido is recebimento_routes.receber_pedido
    assert pedidos_compra_routes.exportar_excel is exportacao_routes.exportar_excel
    assert pedidos_compra_routes.exportar_pdf is exportacao_routes.exportar_pdf
    assert (
        pedidos_compra_routes.sugerir_pedido_inteligente
        is sugestao_routes.sugerir_pedido_inteligente
    )


def test_pedidos_compra_routes_split_mantem_arquivos_focados():
    limits = {
        "app/pedidos_compra_routes.py": 100,
        "app/pedidos_compra/schemas.py": 120,
        "app/pedidos_compra/core_routes.py": 500,
        "app/pedidos_compra/envio_routes.py": 350,
        "app/pedidos_compra/recebimento_routes.py": 250,
        "app/pedidos_compra/exportacao_routes.py": 150,
        "app/pedidos_compra/sugestao_routes.py": 400,
    }

    for relative_path, max_lines in limits.items():
        assert _line_count(relative_path) < max_lines, relative_path
