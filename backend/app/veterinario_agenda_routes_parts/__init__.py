"""Subrouters de agenda veterinaria."""

from .agendamentos_routes import router as agendamentos_router
from .cadastros_routes import router as cadastros_router
from .calendario_routes import router as calendario_router
from .pets_routes import router as pets_router

__all__ = [
    "agendamentos_router",
    "cadastros_router",
    "calendario_router",
    "pets_router",
]
