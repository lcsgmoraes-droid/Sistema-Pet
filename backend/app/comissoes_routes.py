"""Fachada das rotas de comissoes.

As implementacoes ficam separadas por responsabilidade para manter este ponto de
entrada estavel e pequeno para o registro em main_routers.py.
"""

from fastapi import APIRouter

from .comissoes_configuracoes_routes import (
    TIPOS_CONFIGURACAO_COMISSAO,
    buscar_configuracao_aplicavel,
    criar_configuracao,
    criar_configuracoes_batch,
    deletar_configuracao,
    duplicar_configuracao,
    router as configuracoes_router,
)
from .comissoes_operacional_routes import (
    atualizar_configuracoes_sistema,
    get_arvore_produtos,
    get_configuracoes_sistema,
    listar_itens_pendentes,
    router as operacional_router,
)
from .comissoes_parceiros_routes import (
    buscar_configuracoes_funcionario,
    listar_funcionarios,
    listar_funcionarios_com_comissao,
    router as parceiros_router,
)
from .comissoes_schema_guard import ensure_comissoes_config_schema

router = APIRouter(prefix="/comissoes", tags=["comissoes"])
router.include_router(parceiros_router)
router.include_router(configuracoes_router)
router.include_router(operacional_router)

__all__ = [
    "TIPOS_CONFIGURACAO_COMISSAO",
    "atualizar_configuracoes_sistema",
    "buscar_configuracao_aplicavel",
    "buscar_configuracoes_funcionario",
    "criar_configuracao",
    "criar_configuracoes_batch",
    "deletar_configuracao",
    "duplicar_configuracao",
    "ensure_comissoes_config_schema",
    "get_arvore_produtos",
    "get_configuracoes_sistema",
    "listar_funcionarios",
    "listar_funcionarios_com_comissao",
    "listar_itens_pendentes",
    "router",
]
