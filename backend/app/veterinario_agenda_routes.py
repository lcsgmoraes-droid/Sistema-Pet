"""Agregador das rotas de agenda veterinaria."""

# ruff: noqa: F401

from fastapi import APIRouter

from .veterinario_agenda_routes_parts import (
    agendamentos_router,
    cadastros_router,
    calendario_router,
    pets_router,
)
from .veterinario_agenda_routes_parts.agendamentos_routes import (
    _validar_consulta_origem_agendamento,
    atualizar_agendamento,
    criar_agendamento,
    desfazer_inicio_agendamento,
    diagnostico_push_agendamento,
    listar_agendamentos,
    remover_agendamento,
)
from .veterinario_agenda_routes_parts.cadastros_routes import (
    atualizar_consultorio,
    criar_consultorio,
    listar_consultorios,
    listar_veterinarios,
    remover_consultorio,
)
from .veterinario_agenda_routes_parts.calendario_routes import (
    baixar_calendario_agenda_vet,
    feed_publico_calendario_agenda_vet,
    obter_calendario_agenda_vet,
    regenerar_token_calendario_agenda_vet,
)
from .veterinario_agenda_routes_parts.pets_routes import listar_pets_vet

router = APIRouter()
router.include_router(cadastros_router)
router.include_router(pets_router)
router.include_router(calendario_router)
router.include_router(agendamentos_router)
