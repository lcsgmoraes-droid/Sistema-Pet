"""Agregador compativel das rotas de pedidos de compra."""

from fastapi import APIRouter

from .pedidos_compra.confronto_routes import (
    _realizar_confronto as _realizar_confronto,
    router as confronto_router,
)
from .pedidos_compra.core_routes import (
    atualizar_pedido,
    buscar_pedido,
    buscar_rascunho_fornecedor,
    criar_pedido,
    listar_pedidos,
    router as core_router,
)
from .pedidos_compra.envio_routes import (
    cancelar_pedido,
    confirmar_pedido,
    enviar_pedido,
    reverter_status,
    router as envio_router,
    status_envio_pedidos,
)
from .pedidos_compra.exportacao_routes import (
    exportar_excel,
    exportar_pdf,
    router as exportacao_router,
)
from .pedidos_compra.recebimento_routes import (
    receber_pedido,
    router as recebimento_router,
)
from .pedidos_compra.schemas import (
    PedidoCompraEnviarRequest,
    PedidoCompraEnvioFormatos,
    PedidoCompraItemRequest,
    PedidoCompraRequest,
    PedidoCompraResponse,
    RecebimentoItemRequest,
    RecebimentoPedidoRequest,
)
from .pedidos_compra.sugestao_routes import (
    router as sugestao_router,
    sugerir_pedido_inteligente,
)

router = APIRouter(prefix="/pedidos-compra", tags=["Pedidos de Compra"])
router.include_router(confronto_router)
router.include_router(core_router)
router.include_router(envio_router)
router.include_router(recebimento_router)
router.include_router(exportacao_router)
router.include_router(sugestao_router)

__all__ = [
    "PedidoCompraEnviarRequest",
    "PedidoCompraEnvioFormatos",
    "PedidoCompraItemRequest",
    "PedidoCompraRequest",
    "PedidoCompraResponse",
    "RecebimentoItemRequest",
    "RecebimentoPedidoRequest",
    "_realizar_confronto",
    "atualizar_pedido",
    "buscar_pedido",
    "buscar_rascunho_fornecedor",
    "cancelar_pedido",
    "confirmar_pedido",
    "criar_pedido",
    "enviar_pedido",
    "exportar_excel",
    "exportar_pdf",
    "listar_pedidos",
    "receber_pedido",
    "reverter_status",
    "router",
    "status_envio_pedidos",
    "sugerir_pedido_inteligente",
]
