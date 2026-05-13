"""Security helpers for authentication flows."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.models import User
from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant


logger = logging.getLogger(__name__)

MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("AUTH_MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCK_MINUTES = int(os.getenv("AUTH_LOGIN_LOCK_MINUTES", "15"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_datetime(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_request_ip(request: Request | None) -> str | None:
    if not request:
        return None

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None

    return request.client.host if request.client else None


def get_user_agent(request: Request | None) -> str | None:
    return request.headers.get("user-agent") if request else None


def is_user_locked(user: User, reference_time: datetime | None = None) -> bool:
    locked_until = normalize_datetime(getattr(user, "locked_until", None))
    if not locked_until:
        return False
    return locked_until > (reference_time or now_utc())


def remaining_lock_seconds(user: User, reference_time: datetime | None = None) -> int:
    locked_until = normalize_datetime(getattr(user, "locked_until", None))
    if not locked_until:
        return 0
    remaining = locked_until - (reference_time or now_utc())
    return max(0, int(remaining.total_seconds()))


def _audit_auth_event(
    db: Session,
    user: User | None,
    action: str,
    request: Request | None,
    details: dict[str, Any] | None = None,
) -> None:
    if not user:
        return

    previous_tenant = get_current_tenant()
    temporary_tenant = previous_tenant is None and getattr(user, "tenant_id", None)

    try:
        if temporary_tenant:
            set_current_tenant(user.tenant_id)

        log_action(
            db=db,
            user_id=user.id,
            action=action,
            entity_type="auth",
            entity_id=user.id,
            ip_address=get_request_ip(request),
            user_agent=get_user_agent(request),
            details=json.dumps(details or {}, ensure_ascii=False),
            tenant_id=getattr(user, "tenant_id", None),
            commit=False,
        )
    except Exception as exc:
        logger.warning("auth_audit_log_failed", extra={"action": action, "error": str(exc)})
    finally:
        if temporary_tenant:
            clear_current_tenant()


def register_failed_login(db: Session, user: User | None, request: Request | None) -> None:
    if not user:
        return

    attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
    user.failed_login_attempts = attempts

    details: dict[str, Any] = {
        "success": False,
        "failed_login_attempts": attempts,
        "lock_threshold": MAX_FAILED_LOGIN_ATTEMPTS,
    }

    if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = now_utc() + timedelta(minutes=LOGIN_LOCK_MINUTES)
        details["locked_until"] = user.locked_until.isoformat()
        details["lock_minutes"] = LOGIN_LOCK_MINUTES
        _audit_auth_event(db, user, "auth.login_locked", request, details)
    else:
        _audit_auth_event(db, user, "auth.login_failed", request, details)


def register_successful_login(db: Session, user: User, request: Request | None) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now_utc()
    user.last_login_ip = get_request_ip(request)
    _audit_auth_event(
        db,
        user,
        "auth.login_success",
        request,
        {"success": True, "last_login_at": user.last_login_at.isoformat()},
    )


def register_email_verified(db: Session, user: User, request: Request | None) -> None:
    _audit_auth_event(
        db,
        user,
        "auth.email_verified",
        request,
        {"email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None},
    )


def register_email_verification_resent(db: Session, user: User, request: Request | None) -> None:
    _audit_auth_event(db, user, "auth.email_verification_resent", request, {"success": True})


def register_account_created(db: Session, user: User, request: Request | None, source: str) -> None:
    _audit_auth_event(
        db,
        user,
        "auth.account_created",
        request,
        {
            "source": source,
            "email_verified": bool(getattr(user, "email_verified", False)),
            "consent_version": getattr(user, "consent_version", None),
            "privacy_version": getattr(user, "privacy_version", None),
        },
    )


def register_password_reset_requested(db: Session, user: User, request: Request | None) -> None:
    _audit_auth_event(db, user, "auth.password_reset_requested", request, {"success": True})


def register_password_changed(db: Session, user: User, request: Request | None, reason: str) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.password_changed_at = now_utc()
    _audit_auth_event(
        db,
        user,
        "auth.password_changed",
        request,
        {"reason": reason, "password_changed_at": user.password_changed_at.isoformat()},
    )


def register_logout(db: Session, user: User, request: Request | None, revoked_sessions: int) -> None:
    _audit_auth_event(
        db,
        user,
        "auth.logout",
        request,
        {"revoked_sessions": revoked_sessions},
    )
