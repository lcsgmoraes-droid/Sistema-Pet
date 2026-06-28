from __future__ import annotations

from app.bling_integration_parts.catalogo import BlingCatalogoMixin
from app.bling_integration_parts.core import BlingAPIBase
from app.bling_integration_parts.notas import BlingNotasMixin


class BlingAPI(BlingNotasMixin, BlingCatalogoMixin, BlingAPIBase):
    """Cliente para integracao com Bling API v3."""

    pass
