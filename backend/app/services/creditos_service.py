"""Operações pré-pagas com fronteira transacional antes da chamada ao provedor.

As funções de escrita confirmam sua própria transação. O chamador deve usar uma
sessão sem outras escritas pendentes e só chamar o provedor quando start_operation
retornar should_execute=True. Um resultado desconhecido NÃO permite tentar de
novo: permanece pendente para conciliação, mesmo após timeout/reinício.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.creditos_models import CreditoLedgerEntry, CreditoOperation, CreditoWallet
from app.services.creditos_catalog import (
    CreditosError,
    get_creditos_mode,
    get_service,
    normalize_tenant_id,
)
from app.tenancy.context import get_current_tenant, tenant_context
from app.tenancy.rls import sync_rls_tenant


QUOTE_TTL_SECONDS = 15 * 60
MAX_PAYLOAD_BYTES = 128 * 1024
_SAFE_CODE = re.compile(r"^[a-zA-Z0-9_.:/-]{1,120}$")


def _now():
    return datetime.now(timezone.utc)


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _iso(value):
    return _aware(value).isoformat() if value else None


def _actor(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CreditosError("invalid_actor", "Usuário inválido.", 400)
    return value


def _operation_id(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as exc:
        raise CreditosError(
            "operation_not_found", "Operação não encontrada.", 404
        ) from exc


@contextmanager
def _scope(db, tenant_id):
    tenant = normalize_tenant_id(tenant_id)
    current = get_current_tenant()
    if current is not None and normalize_tenant_id(current) != tenant:
        raise CreditosError(
            "tenant_mismatch", "Empresa diferente da sessão atual.", 403
        )
    with tenant_context(tenant):
        sync_rls_tenant(db, tenant)
        yield UUID(tenant)


def _json_bytes(payload):
    if not isinstance(payload, dict):
        raise CreditosError(
            "invalid_payload", "Os dados devem ser um objeto JSON.", 400
        )
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise CreditosError(
            "invalid_payload", "Os dados não são um JSON válido.", 400
        ) from exc
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise CreditosError(
            "payload_too_large", "Os dados excedem o tamanho permitido.", 413
        )
    return encoded


def _fingerprint(actor, service_code, payload):
    return hashlib.sha256(
        str(actor).encode()
        + b"\n"
        + service_code.encode()
        + b"\n"
        + _json_bytes(payload)
    ).hexdigest()


def _usage(value=None):
    """Somente metadados técnicos; jamais prompt, credencial ou payload de erro."""
    value = value if isinstance(value, dict) else {}
    output = {"provider_cost_cents": None, "provider_cost_status": "not_reconciled"}
    for key in ("provider", "model", "provider_request_id", "provider_response_id"):
        item = value.get(key)
        if (
            isinstance(item, str)
            and _SAFE_CODE.fullmatch(item)
            and not item.lower().startswith(("sk-", "bearer"))
        ):
            output[key] = item
    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_tokens",
        "image_count",
        "search_count",
        "web_search_calls",
        "image_tokens",
        "text_tokens",
        "duration_ms",
    ):
        item = value.get(key)
        if isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 10**12:
            output[key] = item
    if isinstance(value.get("response_received"), bool):
        output["response_received"] = value["response_received"]
    return output


def _load(db, tenant, actor, op_id, *, lock=False):
    statement = (
        select(CreditoOperation)
        .where(
            CreditoOperation.tenant_id == tenant,
            CreditoOperation.actor_user_id == _actor(actor),
            CreditoOperation.id == _operation_id(op_id),
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        statement = statement.with_for_update()
    operation = db.execute(statement).scalar_one_or_none()
    if operation is None:
        raise CreditosError("operation_not_found", "Operação não encontrada.", 404)
    return operation


def _serialize(operation, *, should_execute=False):
    return {
        "operation_id": str(operation.id),
        "service_code": operation.service_code,
        "title": operation.title,
        "credits": operation.credits,
        "quoted_credits": operation.credits,
        "price_cents": operation.price_cents,
        "tariff_version": operation.tariff_version,
        "mode": operation.mode,
        "status": operation.status,
        "actor_user_id": operation.actor_user_id,
        "expires_at": _iso(operation.expires_at),
        "created_at": _iso(operation.created_at),
        "completed_at": _iso(operation.completed_at),
        "should_execute": should_execute,
        "result_payload": operation.result_payload,
        "usage_metadata": operation.usage_metadata,
        "failure_code": operation.failure_code,
    }


def _wallet_snapshot(db, tenant):
    row = (
        db.execute(
            select(
                CreditoWallet.available_credits,
                CreditoWallet.reserved_credits,
                CreditoWallet.version,
            ).where(CreditoWallet.tenant_id == tenant)
        )
        .mappings()
        .first()
    )
    return {
        "available_credits": int(row["available_credits"]) if row else 0,
        "reserved_credits": int(row["reserved_credits"]) if row else 0,
        "version": int(row["version"]) if row else 0,
        "wallet_exists": row is not None,
    }


def _move_wallet(db, tenant, *, available_delta, reserved_delta):
    """CAS do saldo: a condição e o débito são uma única escrita no banco."""
    statement = (
        update(CreditoWallet)
        .where(
            CreditoWallet.tenant_id == tenant,
            CreditoWallet.available_credits >= max(0, -available_delta),
            CreditoWallet.reserved_credits >= max(0, -reserved_delta),
        )
        .values(
            available_credits=CreditoWallet.available_credits + available_delta,
            reserved_credits=CreditoWallet.reserved_credits + reserved_delta,
            version=CreditoWallet.version + 1,
            updated_at=_now(),
        )
        .execution_options(synchronize_session=False)
    )
    if db.execute(statement).rowcount != 1:
        code = (
            "insufficient_credits"
            if available_delta < 0
            else "credit_balance_inconsistent"
        )
        message = (
            "Saldo de créditos insuficiente."
            if available_delta < 0
            else "A reserva precisa de conciliação."
        )
        raise CreditosError(code, message, 402 if available_delta < 0 else 409)
    return _wallet_snapshot(db, tenant)


def _ledger(db, operation, kind, *, available_delta=0, reserved_delta=0, wallet=None):
    db.add(
        CreditoLedgerEntry(
            id=str(uuid4()),
            tenant_id=operation.tenant_id,
            operation_id=operation.id,
            actor_user_id=operation.actor_user_id,
            event_key=f"{operation.id}:{kind}",
            kind=kind,
            service_code=operation.service_code,
            title=operation.title,
            credits=operation.credits,
            mode=operation.mode,
            available_delta=available_delta,
            reserved_delta=reserved_delta,
            available_after=wallet["available_credits"] if wallet else None,
            reserved_after=wallet["reserved_credits"] if wallet else None,
        )
    )


def quote(
    db, tenant_id, actor_user_id, service_code, request_payload, *, idempotency_key
):
    """Cotação com preço congelado; não cria carteira nem reserva saldo."""
    actor = _actor(actor_user_id)
    service = get_service(service_code)
    key = str(idempotency_key or "").strip()
    if not 8 <= len(key) <= 128 or not re.fullmatch(r"[a-zA-Z0-9_.:-]+", key):
        raise CreditosError(
            "invalid_idempotency_key", "Identificador da operação inválido.", 400
        )
    fingerprint = _fingerprint(actor, service_code, request_payload)
    with _scope(db, tenant_id) as tenant:
        mode = get_creditos_mode(tenant)
        if mode == "off":
            raise CreditosError(
                "creditos_disabled",
                "Créditos ainda não habilitados para esta empresa.",
                503,
            )
        existing = db.execute(
            select(CreditoOperation).where(
                CreditoOperation.tenant_id == tenant,
                CreditoOperation.idempotency_key == key,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return _existing_quote(existing, actor, service_code, fingerprint, mode)
        operation = CreditoOperation(
            id=str(uuid4()),
            tenant_id=tenant,
            actor_user_id=actor,
            idempotency_key=key,
            request_fingerprint=fingerprint,
            service_code=service_code,
            title=service["title"],
            credits=service["credits"],
            price_cents=service["price_cents"],
            tariff_version=service["tariff_version"],
            mode=mode,
            status="quoted",
            expires_at=_now() + timedelta(seconds=QUOTE_TTL_SECONDS),
        )
        db.add(operation)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            sync_rls_tenant(db, tenant)
            existing = db.execute(
                select(CreditoOperation).where(
                    CreditoOperation.tenant_id == tenant,
                    CreditoOperation.idempotency_key == key,
                )
            ).scalar_one_or_none()
            if existing is None:
                raise
            return _existing_quote(existing, actor, service_code, fingerprint, mode)
        return _serialize(_load(db, tenant, actor, operation.id))


def _existing_quote(operation, actor, service_code, fingerprint, mode):
    if (
        operation.actor_user_id != actor
        or operation.service_code != service_code
        or operation.request_fingerprint != fingerprint
    ):
        raise CreditosError(
            "idempotency_conflict", "Este identificador já foi usado com outros dados."
        )
    if operation.status == "quoted":
        _check_quote(operation, mode)
    return _serialize(operation)


def _check_quote(operation, mode):
    if operation.mode != mode or mode == "off":
        raise CreditosError(
            "credit_mode_changed", "A configuração mudou. Faça uma nova cotação."
        )
    if _aware(operation.expires_at) <= _now():
        raise CreditosError(
            "quote_expired", "A cotação expirou. Faça uma nova cotação."
        )


def get_operation(db, tenant_id, actor_user_id, op_id):
    with _scope(db, tenant_id) as tenant:
        return _serialize(_load(db, tenant, actor_user_id, op_id))


def start_operation(db, tenant_id, actor_user_id, op_id, service_code, request_payload):
    """Apenas quem recebe should_execute=True pode iniciar a chamada externa."""
    actor = _actor(actor_user_id)
    get_service(service_code)
    fingerprint = _fingerprint(actor, service_code, request_payload)
    with _scope(db, tenant_id) as tenant:
        try:
            operation = _load(db, tenant, actor, op_id, lock=True)
            if (
                operation.service_code != service_code
                or operation.request_fingerprint != fingerprint
            ):
                raise CreditosError(
                    "operation_payload_mismatch", "Os dados mudaram desde a cotação."
                )
            if operation.status != "quoted":
                result = _serialize(operation)
                db.commit()
                return result
            _check_quote(operation, get_creditos_mode(tenant))
            claimed = db.execute(
                update(CreditoOperation)
                .where(
                    CreditoOperation.id == operation.id,
                    CreditoOperation.tenant_id == tenant,
                    CreditoOperation.status == "quoted",
                )
                .values(status="running", started_at=_now(), updated_at=_now())
                .execution_options(synchronize_session=False)
            ).rowcount
            if claimed != 1:
                db.rollback()
                return get_operation(db, tenant, actor, op_id)
            if operation.mode == "enforced":
                wallet = _move_wallet(
                    db,
                    tenant,
                    available_delta=-operation.credits,
                    reserved_delta=operation.credits,
                )
                _ledger(
                    db,
                    operation,
                    "reserve",
                    available_delta=-operation.credits,
                    reserved_delta=operation.credits,
                    wallet=wallet,
                )
            db.commit()
            return _serialize(_load(db, tenant, actor, op_id), should_execute=True)
        except Exception:
            db.rollback()
            raise


def complete_operation(
    db, tenant_id, actor_user_id, op_id, *, result_payload, usage_metadata=None
):
    with _scope(db, tenant_id) as tenant:
        try:
            operation = _load(db, tenant, actor_user_id, op_id, lock=True)
            if operation.status == "completed":
                result = _serialize(operation)
                db.commit()
                return result
            if operation.status not in {"running", "uncertain"}:
                raise CreditosError(
                    "operation_not_running", "A operação não está em execução."
                )
            result_copy = json.loads(_json_bytes(result_payload))
            claimed = db.execute(
                update(CreditoOperation)
                .where(
                    CreditoOperation.id == operation.id,
                    CreditoOperation.tenant_id == tenant,
                    CreditoOperation.status.in_(["running", "uncertain"]),
                )
                .values(
                    status="completed",
                    result_payload=result_copy,
                    usage_metadata=_usage(usage_metadata),
                    completed_at=_now(),
                    updated_at=_now(),
                    failure_code=None,
                )
                .execution_options(synchronize_session=False)
            ).rowcount
            if claimed != 1:
                db.rollback()
                return get_operation(db, tenant, actor_user_id, op_id)
            if operation.mode == "enforced":
                wallet = _move_wallet(
                    db, tenant, available_delta=0, reserved_delta=-operation.credits
                )
                _ledger(
                    db,
                    operation,
                    "capture",
                    reserved_delta=-operation.credits,
                    wallet=wallet,
                )
            else:
                _ledger(db, operation, "shadow_usage")
            db.commit()
            return _serialize(_load(db, tenant, actor_user_id, op_id))
        except Exception:
            db.rollback()
            raise


def fail_operation(
    db,
    tenant_id,
    actor_user_id,
    op_id,
    *,
    failure_code,
    definite_failure=False,
    usage_metadata=None,
):
    """Só falha comprovada libera a reserva; timeout/incerteza nunca a libera."""
    if not isinstance(definite_failure, bool):
        raise CreditosError("invalid_failure", "Classificação de falha inválida.", 400)
    if not isinstance(failure_code, str) or not re.fullmatch(
        r"[a-z][a-z0-9_]{0,63}", failure_code
    ):
        raise CreditosError("invalid_failure", "Código de falha inválido.", 400)
    with _scope(db, tenant_id) as tenant:
        try:
            operation = _load(db, tenant, actor_user_id, op_id, lock=True)
            if operation.status in {"completed", "failed"}:
                result = _serialize(operation)
                db.commit()
                return result
            if operation.status not in {"running", "uncertain"}:
                raise CreditosError(
                    "operation_not_running", "A operação não está em execução."
                )
            status = "failed" if definite_failure else "uncertain"
            claimed = db.execute(
                update(CreditoOperation)
                .where(
                    CreditoOperation.id == operation.id,
                    CreditoOperation.tenant_id == tenant,
                    CreditoOperation.status.in_(["running", "uncertain"]),
                )
                .values(
                    status=status,
                    failure_code=failure_code,
                    usage_metadata=_usage(usage_metadata)
                    if usage_metadata is not None
                    else operation.usage_metadata,
                    completed_at=_now() if definite_failure else None,
                    updated_at=_now(),
                )
                .execution_options(synchronize_session=False)
            ).rowcount
            if claimed != 1:
                db.rollback()
                return get_operation(db, tenant, actor_user_id, op_id)
            if definite_failure and operation.mode == "enforced":
                wallet = _move_wallet(
                    db,
                    tenant,
                    available_delta=operation.credits,
                    reserved_delta=-operation.credits,
                )
                _ledger(
                    db,
                    operation,
                    "release",
                    available_delta=operation.credits,
                    reserved_delta=-operation.credits,
                    wallet=wallet,
                )
            db.commit()
            return _serialize(_load(db, tenant, actor_user_id, op_id))
        except Exception:
            db.rollback()
            raise


def get_wallet(db, tenant_id):
    with _scope(db, tenant_id) as tenant:
        return {
            **_wallet_snapshot(db, tenant),
            "mode": get_creditos_mode(tenant),
            "checkout_enabled": False,
        }


def get_ledger(db, tenant_id, *, limit=50, offset=0):
    if (
        isinstance(limit, bool)
        or isinstance(offset, bool)
        or not isinstance(limit, int)
        or not isinstance(offset, int)
        or not 1 <= limit <= 100
        or offset < 0
    ):
        raise CreditosError("invalid_pagination", "Paginação inválida.", 400)
    with _scope(db, tenant_id) as tenant:
        rows = (
            db.execute(
                select(CreditoLedgerEntry)
                .where(CreditoLedgerEntry.tenant_id == tenant)
                .order_by(
                    CreditoLedgerEntry.created_at.desc(), CreditoLedgerEntry.id.desc()
                )
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return {
            "items": [
                {
                    "id": str(row.id),
                    "operation_id": str(row.operation_id) if row.operation_id else None,
                    "created_at": _iso(row.created_at),
                    "service_code": row.service_code,
                    "title": row.title,
                    "credits": row.credits,
                    "kind": row.kind,
                    "mode": row.mode,
                    "available_delta": row.available_delta,
                    "reserved_delta": row.reserved_delta,
                    "available_after": row.available_after,
                    "reserved_after": row.reserved_after,
                }
                for row in rows
            ],
            "limit": limit,
            "offset": offset,
        }
