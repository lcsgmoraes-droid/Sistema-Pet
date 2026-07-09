from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.models import Cliente, User, UserPushDevice

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushTarget:
    token: str
    device: Any | None = None


def _clean_token(token: Any) -> str:
    return str(token or "").strip()


def _dedupe_targets(targets: list[PushTarget]) -> list[PushTarget]:
    seen: set[str] = set()
    unique: list[PushTarget] = []
    for target in targets:
        token = _clean_token(target.token)
        if not token or token in seen:
            continue
        seen.add(token)
        unique.append(PushTarget(token=token, device=target.device))
    return unique


def _legacy_target(token: Any) -> list[PushTarget]:
    cleaned = _clean_token(token)
    return [PushTarget(token=cleaned)] if cleaned else []


def load_user_push_targets(
    db,
    *,
    tenant_id,
    user_id: int | None,
    legacy_push_token: str | None = None,
) -> list[PushTarget]:
    if not user_id:
        return _legacy_target(legacy_push_token)

    targets: list[PushTarget] = []
    try:
        devices = (
            db.query(UserPushDevice)
            .filter(
                UserPushDevice.user_id == user_id,
                UserPushDevice.tenant_id == tenant_id,
                UserPushDevice.enabled.is_(True),
            )
            .order_by(UserPushDevice.last_seen_at.desc())
            .all()
        )
    except Exception as exc:
        logger.warning("[PushDevices] Falha ao consultar dispositivos push: %s", exc)
        devices = []

    for device in devices:
        token = _clean_token(getattr(device, "expo_push_token", None))
        if token:
            targets.append(PushTarget(token=token, device=device))

    if targets:
        return _dedupe_targets(targets)
    return _legacy_target(legacy_push_token)


def load_customer_push_targets(
    db,
    *,
    tenant_id,
    customer_id: int | None,
    legacy_push_token: str | None = None,
) -> list[PushTarget]:
    if not customer_id:
        return _legacy_target(legacy_push_token)

    try:
        cliente = (
            db.query(Cliente)
            .filter(
                Cliente.id == customer_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )
    except Exception as exc:
        logger.warning("[PushDevices] Falha ao consultar cliente do push: %s", exc)
        cliente = None

    if not cliente:
        return _legacy_target(legacy_push_token)

    user_id = getattr(cliente, "user_id", None)
    cliente_email = _clean_token(getattr(cliente, "email", None)).lower()
    email_user = None
    if cliente_email:
        try:
            email_user = (
                db.query(User)
                .filter(
                    User.email == cliente_email,
                    User.tenant_id == tenant_id,
                )
                .first()
            )
        except Exception as exc:
            logger.warning(
                "[PushDevices] Falha ao consultar usuario do push por email: %s",
                exc,
            )

    if email_user:
        targets = load_user_push_targets(
            db,
            tenant_id=tenant_id,
            user_id=getattr(email_user, "id", None),
            legacy_push_token=legacy_push_token
            or getattr(email_user, "push_token", None),
        )
        if targets:
            return targets

    if not user_id:
        return _legacy_target(legacy_push_token)

    user = None
    try:
        user = (
            db.query(User)
            .filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            )
            .first()
        )
    except Exception as exc:
        logger.warning("[PushDevices] Falha ao consultar usuario do push: %s", exc)

    fallback = legacy_push_token or getattr(user, "push_token", None)
    return load_user_push_targets(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        legacy_push_token=fallback,
    )


def mark_push_target_result(
    target: PushTarget,
    *,
    sent: bool,
    ticket_id: str | None = None,
    error: str | None = None,
) -> None:
    device = target.device
    if not getattr(device, "id", None):
        return

    now = datetime.now(timezone.utc)
    if sent:
        device.last_success_at = now
        device.last_ticket_id = ticket_id
        device.last_error = None
        device.last_error_at = None
        return

    device.last_error = error or "Falha ao enviar push"
    device.last_error_at = now
    if "DeviceNotRegistered" in device.last_error:
        device.enabled = False
