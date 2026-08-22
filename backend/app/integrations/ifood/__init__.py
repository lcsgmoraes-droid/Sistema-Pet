"""Componentes da integracao com a iFood Merchant API."""

from .catalog import IfoodCatalogItem, build_catalog_item, build_catalog_preview
from .client import IfoodClient, IfoodClientError
from .orders import (
    mark_order_action,
    order_detail,
    order_summary,
    process_order_events,
    upsert_ifood_order,
)

__all__ = [
    "IfoodCatalogItem",
    "IfoodClient",
    "IfoodClientError",
    "build_catalog_item",
    "build_catalog_preview",
    "mark_order_action",
    "order_detail",
    "order_summary",
    "process_order_events",
    "upsert_ifood_order",
]
