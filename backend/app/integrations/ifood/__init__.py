"""Componentes da integracao com a iFood Merchant API."""

from .catalog import IfoodCatalogItem, build_catalog_item, build_catalog_preview
from .client import IfoodClient, IfoodClientError

__all__ = [
    "IfoodCatalogItem",
    "IfoodClient",
    "IfoodClientError",
    "build_catalog_item",
    "build_catalog_preview",
]
