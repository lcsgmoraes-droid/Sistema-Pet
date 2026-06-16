from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import or_

from app.db import SessionLocal
from app.ops_models import OpsAlert, OpsErrorEvent


DEFAULT_PATH_PREFIXES = ("/integracoes/bling/",)


def _uuid_text(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _tenant_id_arg(value: str | None) -> str:
    tenant_id = _uuid_text(
        value
        or os.getenv("OPS_BACKFILL_TENANT_ID")
        or os.getenv("BLING_WEBHOOK_TENANT_ID")
    )
    if not tenant_id:
        raise SystemExit(
            "Informe --tenant-id ou configure OPS_BACKFILL_TENANT_ID/BLING_WEBHOOK_TENANT_ID com UUID valido."
        )
    return tenant_id


def _prefixes_arg(values: list[str] | None) -> tuple[str, ...]:
    prefixes = tuple(
        value.strip()
        for value in (values or list(DEFAULT_PATH_PREFIXES))
        if value.strip()
    )
    if not prefixes:
        raise SystemExit("Informe ao menos um --path-prefix.")
    return prefixes


def _path_filters(model, prefixes: Iterable[str]):
    return [model.path.like(f"{prefix}%") for prefix in prefixes]


def backfill_ops_events(
    *,
    tenant_id: str,
    path_prefixes: tuple[str, ...],
    hours: int | None,
    resolve_alerts: bool,
) -> dict[str, int | str | list[str] | None]:
    db = SessionLocal()
    try:
        since = None
        if hours and hours > 0:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = db.query(OpsErrorEvent).filter(
            OpsErrorEvent.tenant_id.is_(None),
            or_(*_path_filters(OpsErrorEvent, path_prefixes)),
        )
        if since is not None:
            query = query.filter(OpsErrorEvent.created_at >= since)

        updated_events = 0
        for row in query.yield_per(200):
            payload = dict(row.payload or {})
            payload["tenant_id"] = tenant_id
            payload["tenant_source"] = "ops_backfill_path_prefix"
            payload["tenant_backfilled_at"] = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            row.tenant_id = UUID(tenant_id)
            row.payload = payload
            db.add(row)
            updated_events += 1

        resolved_alerts = 0
        if resolve_alerts:
            alert_query = db.query(OpsAlert).filter(
                OpsAlert.status == "open",
                OpsAlert.tenant_id.is_(None),
                or_(
                    OpsAlert.alert_key.like("tenant:sem_tenant:%"),
                    *_path_filters(OpsAlert, path_prefixes),
                ),
            )
            now = datetime.now(timezone.utc)
            for alert in alert_query.yield_per(100):
                payload = dict(alert.payload or {})
                payload["resolved_by"] = "ops_tenant_backfill"
                payload["resolved_reason"] = (
                    "Eventos sem tenant foram reatribuidos por prefixo de rota."
                )
                alert.status = "resolved"
                alert.resolved_at = now
                alert.updated_at = now
                alert.payload = payload
                db.add(alert)
                resolved_alerts += 1

        db.commit()
        return {
            "tenant_id": tenant_id,
            "path_prefixes": list(path_prefixes),
            "hours": hours,
            "updated_events": updated_events,
            "resolved_alerts": resolved_alerts,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atribui tenant a eventos Ops historicos que nasceram sem tenant em rotas conhecidas."
    )
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--path-prefix", action="append", default=None)
    parser.add_argument(
        "--hours",
        type=int,
        default=72,
        help="Janela a corrigir. Use 0 para todo o historico.",
    )
    parser.add_argument("--keep-alerts-open", action="store_true")
    args = parser.parse_args()

    result = backfill_ops_events(
        tenant_id=_tenant_id_arg(args.tenant_id),
        path_prefixes=_prefixes_arg(args.path_prefix),
        hours=args.hours,
        resolve_alerts=not args.keep_alerts_open,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
