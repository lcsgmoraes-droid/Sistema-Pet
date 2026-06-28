"""Agregador das rotas de sugestoes inteligentes para racoes."""

from fastapi import APIRouter

from app.racoes_sugestoes_common import (
    _produto_eh_racao_expr as _produto_eh_racao_expr,
    _validar_tenant_e_obter_usuario as _validar_tenant_e_obter_usuario,
)
from app.racoes_sugestoes_duplicatas_routes import (
    detectar_duplicatas as detectar_duplicatas,
    ignorar_duplicata as ignorar_duplicata,
    mesclar_produtos as mesclar_produtos,
    router as duplicatas_router,
)
from app.racoes_sugestoes_gaps_routes import (
    identificar_gaps_estoque as identificar_gaps_estoque,
    router as gaps_router,
)
from app.racoes_sugestoes_padronizacao_routes import (
    router as padronizacao_router,
    sugerir_padronizacao_nomes as sugerir_padronizacao_nomes,
)
from app.racoes_sugestoes_relatorio_routes import (
    obter_relatorio_completo as obter_relatorio_completo,
    router as relatorio_router,
)
from app.racoes_sugestoes_schemas import (
    DuplicataDetectada as DuplicataDetectada,
    GapEstoque as GapEstoque,
    PadronizacaoNome as PadronizacaoNome,
)


router = APIRouter(prefix="/racoes/sugestoes", tags=["Sugestões Inteligentes - Rações"])
router.include_router(duplicatas_router)
router.include_router(padronizacao_router)
router.include_router(gaps_router)
router.include_router(relatorio_router)


__all__ = [
    "DuplicataDetectada",
    "GapEstoque",
    "PadronizacaoNome",
    "_produto_eh_racao_expr",
    "_validar_tenant_e_obter_usuario",
    "detectar_duplicatas",
    "identificar_gaps_estoque",
    "ignorar_duplicata",
    "mesclar_produtos",
    "obter_relatorio_completo",
    "router",
    "sugerir_padronizacao_nomes",
]
