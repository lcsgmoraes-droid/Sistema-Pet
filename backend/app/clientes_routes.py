# ruff: noqa: F401
"""Fachada das rotas de clientes, fornecedores, pets e pessoas operacionais."""

from fastapi import APIRouter

from app.clientes.common import (
    _anexar_metadados_criacao_cliente,
    _obter_cliente_ou_404,
    _somente_digitos,
    _somente_digitos_coluna,
    _validar_telefone_cliente_obrigatorio,
    _validar_tenant_e_obter_usuario,
    gerar_codigo_cliente,
)
from app.clientes.credito_routes import (
    adicionar_credito,
    remover_campo_duplicado,
    remover_credito,
    router as credito_router,
)
from app.clientes.crud_routes import (
    base_router as clientes_base_router,
    create_cliente,
    delete_cliente,
    detail_router as clientes_detail_router,
    get_cliente,
    list_clientes,
    update_cliente,
)
from app.clientes.duplicidades_routes import (
    executar_fusao_pessoas_route,
    executar_fusoes_automaticas_pessoas_route,
    listar_sugestoes_duplicidade_pessoas_route,
    preview_fusao_pessoas,
    router as duplicidades_router,
    verificar_duplicata,
)
from app.clientes.financeiro_routes import (
    baixar_vendas_lote,
    get_cliente_historico,
    get_extrato_credito,
    get_historico_compras,
    get_vendas_em_aberto,
    router as financeiro_router,
)
from app.clientes.parceiros_routes import (
    atualizar_controla_dre,
    obter_custo_operacional_entregador,
    router as parceiros_router,
    toggle_parceiro,
)
from app.clientes.pets_routes import (
    _pet_response_dict,
    create_pet,
    delete_pet,
    get_pet,
    list_pets_by_cliente,
    listar_todos_pets,
    router as pets_router,
    update_pet,
)
from app.clientes.racas_routes import (
    list_racas,
    list_racas_teste,
    router as racas_router,
)
from app.clientes.schemas import (
    AjustarCreditoRequest,
    ClienteCreate,
    ClienteResponse,
    ClientesListResponse,
    ClienteUpdate,
    PessoaFusaoExecutarRequest,
    PessoaFusaoPreviewRequest,
    PetCreate,
    PetResponse,
    PetUpdate,
    ToggleParceiroRequest,
)
from app.clientes.timeline_routes import (
    TimelineEvento,
    _obter_timeline,
    obter_timeline_cliente,
    obter_timeline_fornecedor,
    router as timeline_router,
)

router = APIRouter(prefix="/clientes", tags=["clientes"])
router.include_router(timeline_router)
router.include_router(financeiro_router)
router.include_router(duplicidades_router)
router.include_router(pets_router)
router.include_router(credito_router)
router.include_router(parceiros_router)
router.include_router(clientes_base_router)
router.include_router(racas_router)
router.include_router(clientes_detail_router)

__all__ = [
    "AjustarCreditoRequest",
    "ClienteCreate",
    "ClienteResponse",
    "ClientesListResponse",
    "ClienteUpdate",
    "PessoaFusaoExecutarRequest",
    "PessoaFusaoPreviewRequest",
    "PetCreate",
    "PetResponse",
    "PetUpdate",
    "TimelineEvento",
    "ToggleParceiroRequest",
    "_anexar_metadados_criacao_cliente",
    "_obter_cliente_ou_404",
    "_obter_timeline",
    "_pet_response_dict",
    "_somente_digitos",
    "_somente_digitos_coluna",
    "_validar_telefone_cliente_obrigatorio",
    "_validar_tenant_e_obter_usuario",
    "adicionar_credito",
    "atualizar_controla_dre",
    "baixar_vendas_lote",
    "create_cliente",
    "create_pet",
    "delete_cliente",
    "delete_pet",
    "executar_fusao_pessoas_route",
    "executar_fusoes_automaticas_pessoas_route",
    "gerar_codigo_cliente",
    "get_cliente",
    "get_cliente_historico",
    "get_extrato_credito",
    "get_historico_compras",
    "get_pet",
    "get_vendas_em_aberto",
    "list_clientes",
    "list_pets_by_cliente",
    "list_racas",
    "list_racas_teste",
    "listar_sugestoes_duplicidade_pessoas_route",
    "listar_todos_pets",
    "obter_custo_operacional_entregador",
    "obter_timeline_cliente",
    "obter_timeline_fornecedor",
    "preview_fusao_pessoas",
    "remover_campo_duplicado",
    "remover_credito",
    "router",
    "toggle_parceiro",
    "update_cliente",
    "update_pet",
    "verificar_duplicata",
]
