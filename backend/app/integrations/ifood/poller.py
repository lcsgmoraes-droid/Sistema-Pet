"""Ciclo multiempresa do polling de pedidos iFood."""

from __future__ import annotations

import logging
from uuid import UUID

from app.config import settings
from app.db import SessionLocal
from app.ifood_integration_models import IfoodMerchantConfig
from app.models import Tenant
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant

from .client import IfoodClient, IfoodClientError
from .orders import process_order_events

logger = logging.getLogger(__name__)


def poll_active_ifood_tenants_once() -> dict[str, int]:
    """Executa um ciclo; cada empresa permanece isolada por contexto e RLS."""

    discovery_db = SessionLocal()
    try:
        tenant_ids = [UUID(str(value)) for (value,) in discovery_db.query(Tenant.id)]
    finally:
        discovery_db.close()

    result = {"tenants": 0, "events": 0, "failures": 0}
    with IfoodClient(
        client_id=settings.IFOOD_CLIENT_ID,
        client_secret=settings.IFOOD_CLIENT_SECRET,
        base_url=settings.IFOOD_API_BASE_URL,
        timeout_seconds=settings.IFOOD_REQUEST_TIMEOUT_SECONDS,
    ) as client:
        for tenant_id in tenant_ids:
            with tenant_context(tenant_id):
                db = SessionLocal()
                try:
                    sync_rls_tenant(db, tenant_id)
                    config = (
                        db.query(IfoodMerchantConfig)
                        .filter(
                            IfoodMerchantConfig.tenant_id == tenant_id,
                            IfoodMerchantConfig.active.is_(True),
                            IfoodMerchantConfig.merchant_id.isnot(None),
                        )
                        .first()
                    )
                    if config is None:
                        continue
                    result["tenants"] += 1
                    summary = process_order_events(
                        db,
                        tenant_id=tenant_id,
                        config=config,
                        client=client,
                    )
                    result["events"] += int(summary["received"])
                except IfoodClientError as exc:
                    db.rollback()
                    result["failures"] += 1
                    config = (
                        db.query(IfoodMerchantConfig)
                        .filter(IfoodMerchantConfig.tenant_id == tenant_id)
                        .first()
                    )
                    if config:
                        config.last_orders_error = str(exc)
                        db.commit()
                    logger.warning(
                        "[IFOOD] Falha sanitizada no polling do tenant %s: %s",
                        tenant_id,
                        exc,
                    )
                except Exception:
                    db.rollback()
                    result["failures"] += 1
                    logger.exception(
                        "[IFOOD] Falha inesperada no polling do tenant %s", tenant_id
                    )
                finally:
                    db.close()
    return result
