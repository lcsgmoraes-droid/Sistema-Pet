"""Subrouters de internacao veterinaria."""

from .agenda_routes import router as agenda_router
from .historico_routes import router as historico_router
from .listagem_config_routes import router as listagem_config_router
from .mutacao_routes import router as mutacao_router

__all__ = [
    "agenda_router",
    "historico_router",
    "listagem_config_router",
    "mutacao_router",
]
