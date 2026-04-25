"""Agregador das rotas do modulo veterinario."""

from fastapi import APIRouter

from .veterinario_acompanhamento_routes import router as acompanhamento_router
from .veterinario_agenda_routes import router as agenda_router
from .veterinario_catalogo_routes import router as catalogo_router
from .veterinario_consultas_routes import router as consultas_router
from .veterinario_exames_routes import router as exames_router
from .veterinario_ia_routes import router as ia_router
from .veterinario_internacao_routes import router as internacao_router
from .veterinario_parcerias_routes import router as parcerias_router
from .veterinario_relatorios_routes import router as relatorios_router

router = APIRouter(prefix="/vet", tags=["Veterinario"])
router.include_router(acompanhamento_router)
router.include_router(agenda_router)
router.include_router(internacao_router)
router.include_router(ia_router)
router.include_router(consultas_router)
router.include_router(exames_router)
router.include_router(catalogo_router)
router.include_router(relatorios_router)
router.include_router(parcerias_router)
