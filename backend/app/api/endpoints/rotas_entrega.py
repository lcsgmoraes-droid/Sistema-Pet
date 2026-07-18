from fastapi import APIRouter

from app.api.endpoints.rotas_entrega_auth import (
    DeliveryActor,
    _activate_delivery_actor_tenant,
    _rota_filters_for_actor,
    _validate_ecommerce_entregador_actor,
)
from app.api.endpoints.rotas_entrega_core_routes import (
    atualizar_rota,
    listar_rotas,
    listar_vendas_pendentes_entrega,
    obter_rota,
    router as core_router,
)
from app.api.endpoints.rotas_entrega_public_routes import rastreio_publico
from app.api.endpoints.rotas_entrega_criacao_routes import (
    criar_rota,
    router as criacao_router,
)
from app.api.endpoints.rotas_entrega_estado_routes import (
    excluir_rota,
    fechar_rota,
    iniciar_rota,
    reverter_inicio_rota,
    router as estado_router,
)
from app.api.endpoints.rotas_entrega_otimizacao_routes import (
    OtimizarSelecionadasRequest,
    otimizar_vendas_pendentes,
    otimizar_vendas_selecionadas,
    router as otimizacao_router,
)
from app.api.endpoints.rotas_entrega_paradas_routes import (
    RegistrarRecebimentoPayload,
    adicionar_observacao_parada,
    atualizar_localizacao_rota,
    listar_paradas_rota,
    marcar_parada_entregue,
    marcar_parada_nao_entregue,
    registrar_recebimento_entregador,
    reordenar_paradas,
    router as paradas_router,
)
from app.api.endpoints.rotas_entrega_schema import ensure_rotas_entrega_schema
from app.api.endpoints.rotas_entrega_tracking import (
    _sincronizar_venda_entregue_por_parada,
)

router = APIRouter(prefix="/rotas-entrega", tags=["Entregas - Rotas"])
router.include_router(core_router)
router.include_router(otimizacao_router)
router.include_router(paradas_router)
router.include_router(criacao_router)
router.include_router(estado_router)

__all__ = [
    "DeliveryActor",
    "OtimizarSelecionadasRequest",
    "RegistrarRecebimentoPayload",
    "_activate_delivery_actor_tenant",
    "_rota_filters_for_actor",
    "_sincronizar_venda_entregue_por_parada",
    "_validate_ecommerce_entregador_actor",
    "adicionar_observacao_parada",
    "atualizar_localizacao_rota",
    "atualizar_rota",
    "criar_rota",
    "ensure_rotas_entrega_schema",
    "excluir_rota",
    "fechar_rota",
    "iniciar_rota",
    "listar_paradas_rota",
    "listar_rotas",
    "listar_vendas_pendentes_entrega",
    "marcar_parada_entregue",
    "marcar_parada_nao_entregue",
    "obter_rota",
    "otimizar_vendas_pendentes",
    "otimizar_vendas_selecionadas",
    "rastreio_publico",
    "registrar_recebimento_entregador",
    "reordenar_paradas",
    "reverter_inicio_rota",
    "router",
]
