"""Estoque absoluto, duravel e exclusivo do SKU 227 no DEV.

O scheduler le o saldo confirmado no banco, incluindo reservas, sem depender de
eventos em memoria. Cada PATCH omite todos os campos fora barcode/inventory.stock.
Nesta etapa o cliente so pode apontar para um servidor falso em loopback; a API
real e bloqueada mesmo com flags/credenciais herdadas. HTTP 202 significa aceite
assincrono, nunca confirmacao de aplicacao. Timeout/5xx/crash exigem conferencia.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import logging
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import text

from app.config import _is_strict_runtime_environment, settings
from app.db import SessionLocal
from app.ifood_catalog_models import (
    IfoodCatalogConfirmation as Confirmation,
    IfoodCatalogLink as Link,
    IfoodCatalogSubmission as Submission,
    IfoodStockSyncState as State,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.produtos_catalogo_models import Produto
from app.tenancy.context import get_current_tenant, tenant_context
from app.tenancy.rls import sync_rls_tenant

from .catalog_pilot import _identity_issues, _last_rows
from .client import IfoodClient, IfoodClientError
from .management import product_identifier

logger = logging.getLogger(__name__)
PILOT_SKU = "227"
PILOT_BARCODE = "7898242031448"
COOLDOWN_SECONDS = 35 * 60
MAX_RATE_LIMIT_RETRIES = 5
MAX_STOCK = 1_000_000
JOB_ID = "ifood_stock_sync_dev_pilot"


def _utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def _local_provider(base_url=None):
    """URL local exata; nao aceita DNS arbitrario, credenciais, rota ou redirect."""
    try:
        parsed = urlsplit(
            str(settings.IFOOD_API_BASE_URL if base_url is None else base_url)
        )
        return (
            parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed.username is None
            and parsed.password is None
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
            and (parsed.port is None or 0 < parsed.port < 65536)
        )
    except (ValueError, TypeError):
        return False


def settings_reason():
    """Fail closed inclusive para os aliases APP_ENV/ENV/ENVIRONMENT."""
    if _is_strict_runtime_environment() or str(
        settings.ENVIRONMENT
    ).strip().lower() not in {"development", "dev", "test", "local"}:
        return "dev_only"
    if (
        not settings.IFOOD_STOCK_SYNC_DEV_ENABLED
        or not settings.IFOOD_STOCK_SYNC_POLLING_ENABLED
    ):
        return "disabled"
    if not settings.IFOOD_CATALOG_WRITE_ENABLED:
        return "catalog_write_disabled"
    if not _local_provider():
        return "provider_not_local"
    try:
        UUID(settings.IFOOD_STOCK_SYNC_TENANT_ID)
        UUID(settings.IFOOD_STOCK_SYNC_MERCHANT_ID)
        if (
            isinstance(settings.IFOOD_STOCK_SYNC_PRODUCT_ID, bool)
            or int(settings.IFOOD_STOCK_SYNC_PRODUCT_ID) <= 0
            or settings.IFOOD_STOCK_SYNC_SKU != PILOT_SKU
            or settings.IFOOD_STOCK_SYNC_BARCODE != PILOT_BARCODE
        ):
            return "scope_invalid"
    except (ValueError, TypeError, AttributeError):
        return "scope_invalid"
    if (
        not str(settings.IFOOD_CLIENT_ID or "").strip()
        or not str(settings.IFOOD_CLIENT_SECRET or "").strip()
    ):
        return "credentials_missing"
    return None


def enabled_for(tenant_id, merchant_id, product_id):
    if settings_reason() is not None:
        return False
    return (
        str(tenant_id) == str(UUID(settings.IFOOD_STOCK_SYNC_TENANT_ID))
        and str(merchant_id) == str(UUID(settings.IFOOD_STOCK_SYNC_MERCHANT_ID))
        and product_id == settings.IFOOD_STOCK_SYNC_PRODUCT_ID
    )


def state_view(row):
    if row is None:
        return None
    return {
        "status": row.status,
        "desired_stock": row.desired_stock,
        "last_accepted_stock": row.last_accepted_stock,
        "reference_source": row.reference_source,
        "next_attempt_at": _utc(row.next_attempt_at).isoformat()
        if row.next_attempt_at
        else None,
        "failure_count": row.failure_count,
        "error_code": row.error_code,
        "external_confirmed": False,
        "environment": "dev",
    }


def stock_sync_view(db, tenant_id, merchant_id, product_id):
    """Leitura local; nunca recalcula/agenda/envia durante um GET."""
    row = (
        db.query(State)
        .join(Link, (Link.tenant_id == State.tenant_id) & (Link.id == State.link_id))
        .filter(
            State.tenant_id == tenant_id,
            State.merchant_id == merchant_id,
            Link.merchant_id == merchant_id,
            Link.product_id == product_id,
        )
        .first()
    )
    result = state_view(row)
    if result:
        result["enabled"] = enabled_for(tenant_id, merchant_id, product_id)
    return result


def register_stock_sync_job(scheduler):
    if settings_reason() is not None:
        return False
    scheduler.add_job(
        poll_ifood_stock_once,
        "interval",
        seconds=max(30, int(settings.IFOOD_STOCK_SYNC_INTERVAL_SECONDS)),
        id=JOB_ID,
        name="iFood estoque: piloto DEV SKU 227",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        misfire_grace_time=60,
    )
    return True


def _advisory_lock(db, tenant, merchant, product_id):
    if db.get_bind().dialect.name != "postgresql":
        return True
    key = int.from_bytes(
        sha256(f"ifood-stock:{tenant}:{merchant}:{product_id}".encode()).digest()[:8],
        "big",
        signed=True,
    )
    return bool(
        db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}
        ).scalar()
    )


def _scope():
    return (
        UUID(settings.IFOOD_STOCK_SYNC_TENANT_ID),
        str(UUID(settings.IFOOD_STOCK_SYNC_MERCHANT_ID)),
        settings.IFOOD_STOCK_SYNC_PRODUCT_ID,
    )


def _target(db, tenant, merchant, product_id):
    if str(get_current_tenant()) != str(tenant):
        return None, "tenant_context_mismatch"
    config = (
        db.query(IfoodMerchantConfig)
        .filter(IfoodMerchantConfig.tenant_id == tenant)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if config is None or not config.active or config.merchant_id != merchant:
        return None, "merchant_inactive"
    product = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant, Produto.id == product_id)
        .populate_existing()
        .first()
    )
    if (
        product is None
        or product.codigo != PILOT_SKU
        or product_identifier(product) != PILOT_BARCODE
    ):
        return None, "product_identity_changed"
    link = (
        db.query(Link)
        .filter(
            Link.tenant_id == tenant,
            Link.merchant_id == merchant,
            Link.product_id == product_id,
        )
        .populate_existing()
        .first()
    )
    if link is None or link.mode != "existing" or link.barcode != PILOT_BARCODE:
        return None, "existing_link_required"
    if _identity_issues(db, tenant, product):
        return None, "product_identity_invalid"
    if (
        product.deleted_at
        or not product.ativo
        or not product.situacao
        or not product.is_sellable
        or not product.anunciar_ifood
        or product.tipo_produto != "SIMPLES"
        or product.e_granel
        or str(product.tipo or "").lower() == "servico"
    ):
        return None, "product_not_sellable"
    return (config, product, link), None


def _integer_stock(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
        if (
            number.is_finite()
            and 0 <= number <= MAX_STOCK
            and number == number.to_integral_value()
        ):
            return int(number)
    except (InvalidOperation, ValueError, TypeError):
        pass
    return None


def _desired_stock(db, tenant, config, product):
    from app.routes.ifood_integration_routes import _available_stocks

    # O helper legado trata NULL como zero. No envio automatico NULL e desconhecido.
    physical = _integer_stock(product.estoque_atual)
    if physical is None:
        return None
    available = _available_stocks(db, tenant, [product]).get(product.id)
    try:
        safety = Decimal(str(config.stock_safety or 0))
        available = Decimal(str(available))
        if not safety.is_finite() or safety < 0 or not available.is_finite():
            return None
        return _integer_stock(
            0 if product.ifood_pausado else max(Decimal(0), available - safety)
        )
    except (InvalidOperation, TypeError, ValueError):
        return None


def _confirmed(last, confirmation, *, known_stock=False):
    return bool(
        confirmation
        and confirmation.present
        and confirmation.barcode == PILOT_BARCODE
        and confirmation.portal_active is True
        and (not last or _utc(confirmation.confirmed_at) > _utc(last.created_at))
        and (not known_stock or _integer_stock(confirmation.stock) is not None)
    )


def _save_status(db, state, status, code=None, *, next_attempt_at=None):
    state.status, state.error_code = status, code
    if next_attempt_at is not None:
        state.next_attempt_at = next_attempt_at
    result = {"status": status, "reason": code, "desired_stock": state.desired_stock}
    db.commit()
    return result


def _observe(db, scope, now):
    tenant, merchant, product_id = scope
    if not _advisory_lock(db, *scope):
        return None, {"status": "busy"}
    target, reason = _target(db, *scope)
    if reason:
        existing = (
            db.query(State)
            .join(
                Link, (Link.tenant_id == State.tenant_id) & (Link.id == State.link_id)
            )
            .filter(
                State.tenant_id == tenant,
                State.merchant_id == merchant,
                Link.product_id == product_id,
            )
            .populate_existing()
            .with_for_update(of=State)
            .first()
        )
        if existing:
            return None, _save_status(db, existing, "blocked", reason)
        return None, {"status": "blocked", "reason": reason}
    config, product, link = target
    state = (
        db.query(State)
        .filter(
            State.tenant_id == tenant,
            State.merchant_id == merchant,
            State.link_id == link.id,
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if state is None:
        state = State(
            tenant_id=tenant,
            merchant_id=merchant,
            link_id=link.id,
            link_revision=link.revision,
            status="queued",
            failure_count=0,
        )
        db.add(state)
        db.flush()
    last = _last_rows(db, tenant, [link.id], Submission).get(link.id)
    confirmation = _last_rows(db, tenant, [link.id], Confirmation).get(link.id)
    reviewed = _confirmed(last, confirmation, known_stock=True)
    if (
        last
        and (last.source or "manual") == "manual"
        and last.status == "accepted"
        and not _confirmed(last, confirmation)
    ):
        return None, _save_status(db, state, "blocked", "manual_pending")
    crash_reviewed = bool(
        reviewed
        and confirmation.kind == "portal"
        and (
            not last
            or now >= _utc(last.created_at) + timedelta(seconds=COOLDOWN_SECONDS)
        )
    )
    if state.link_revision != link.revision:
        # A conferencia humana legitima incrementa a revisao. Uma nova ligacao
        # ou revisao sem prova posterior nao pode liberar o envio automatico.
        if not crash_reviewed or state.last_confirmation_id == confirmation.id:
            return None, _save_status(db, state, "blocked", "link_revision_changed")
        state.link_revision = link.revision
    if state.last_confirmation_id is None and not reviewed:
        return None, _save_status(db, state, "blocked", "initial_confirmation_required")
    if confirmation and state.last_confirmation_id != confirmation.id:
        if _confirmed(last, confirmation, known_stock=True):
            state.last_accepted_stock = _integer_stock(confirmation.stock)
            state.reference_source = "portal"
            state.failure_count = 0
            if not last or last.status != "sending":
                state.error_code = None
                state.status = "queued"
        state.last_confirmation_id = confirmation.id
    state.desired_stock = _desired_stock(db, tenant, config, product)
    if state.desired_stock is None:
        return None, _save_status(db, state, "blocked", "stock_invalid")
    if last:
        source = last.source or "manual"
        if last.status == "sending" and not crash_reviewed:
            return None, _save_status(db, state, "uncertain", "sending_requires_review")
        if last.status == "uncertain" and not reviewed:
            return None, _save_status(
                db, state, "uncertain", "external_result_uncertain"
            )
        if source == "auto_stock" and last.request_key != state.last_request_key:
            return None, _save_status(db, state, "blocked", "attempt_identity_changed")
        if (
            source == "auto_stock"
            and last.status == "error"
            and last.http_status != 429
            and last.error_code != "dispatch_aborted"
            and not reviewed
        ):
            return None, _save_status(db, state, "blocked", "provider_rejected")
        if (
            last.http_status == 429
            and state.failure_count >= MAX_RATE_LIMIT_RETRIES
            and not reviewed
        ):
            return None, _save_status(db, state, "blocked", "retry_limit")
        window = _utc(last.created_at) + timedelta(seconds=COOLDOWN_SECONDS)
        if (
            last.status in {"accepted", "sending", "uncertain"}
            or last.http_status == 429
        ):
            state.next_attempt_at = (
                max(window, _utc(state.next_attempt_at))
                if state.next_attempt_at
                else window
            )
    # Um 429 nao substitui o ultimo aceite: se o saldo desejado voltou para o
    # ultimo aceito, nao ha PATCH pendente e nao se repete uma tentativa inutil.
    if state.desired_stock == state.last_accepted_stock:
        state.status, state.error_code = "accepted", None
        result = {"status": "unchanged", "desired_stock": state.desired_stock}
        db.commit()
        return None, result
    if state.next_attempt_at and _utc(state.next_attempt_at) > now:
        status = "backoff" if last and last.http_status == 429 else "queued"
        result = _save_status(db, state, status, "cooldown")
        result["status"] = "backoff" if status == "backoff" else "cooldown"
        return None, result
    return (config, product, link, state), None


def _client():
    base_url = str(settings.IFOOD_API_BASE_URL or "")
    if not _local_provider(base_url):
        raise IfoodClientError(
            "O piloto DEV exige provedor local falso.", status_code=400
        )
    return IfoodClient(
        client_id=settings.IFOOD_CLIENT_ID,
        client_secret=settings.IFOOD_CLIENT_SECRET,
        base_url=base_url,
        timeout_seconds=min(15, max(1, settings.IFOOD_REQUEST_TIMEOUT_SECONDS)),
        trust_env=False,
    )


def _preflight(db, scope, link_revision, sent_stock):
    if settings_reason() is not None or _scope() != scope:
        return "scope_changed"
    target, reason = _target(db, *scope)
    if reason:
        return reason
    config, product, link = target
    if link.revision != link_revision:
        return "link_revision_changed"
    if _desired_stock(db, scope[0], config, product) != sent_stock:
        return "stock_changed_before_dispatch"
    return None


def _dispatch(db, target, scope, now, client_factory):
    config, product, link, state = target
    payload = {"barcode": PILOT_BARCODE, "inventory": {"stock": state.desired_stock}}
    request_key = str(uuid4())
    row = Submission(
        tenant_id=scope[0],
        link_id=link.id,
        merchant_id=scope[1],
        barcode=PILOT_BARCODE,
        request_key=request_key,
        operation="update",
        source="auto_stock",
        fields=["stock"],
        payload_hash=sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        evidence=payload,
        status="sending",
        actor_id=link.portal_checked_by,
        created_at=now,
    )
    link_revision = link.revision
    db.add(row)
    state.status, state.error_code, state.last_request_key = (
        "sending",
        None,
        request_key,
    )
    state.next_attempt_at = now + timedelta(seconds=COOLDOWN_SECONDS)
    # Duravel antes da rede, visivel a outros workers e ao fluxo manual.
    db.commit()
    sent_stock = payload["inventory"]["stock"]
    db.expire_all()
    sync_rls_tenant(db, scope[0])
    preflight_reason = _preflight(db, scope, link_revision, sent_stock)
    if preflight_reason:
        row = (
            db.query(Submission)
            .filter_by(
                tenant_id=scope[0], merchant_id=scope[1], request_key=request_key
            )
            .one()
        )
        state = (
            db.query(State)
            .filter_by(tenant_id=scope[0], merchant_id=scope[1], link_id=row.link_id)
            .one()
        )
        row.status, row.error_code, row.finished_at = "error", "dispatch_aborted", now
        state.status = (
            "queued"
            if preflight_reason == "stock_changed_before_dispatch"
            else "blocked"
        )
        state.error_code, state.next_attempt_at = "dispatch_aborted", None
        result = {
            "status": state.status,
            "reason": preflight_reason,
            "request_key": request_key,
        }
        db.commit()
        return result
    # A conferencia leu dados frescos apos o claim. Libere a configuracao antes
    # da rede para nao reter um lock operacional durante o timeout do provedor.
    db.commit()
    try:
        with client_factory() as client:
            result = client.ingest_items(
                scope[1], [payload], method="PATCH", reset_catalog=False
            )
        http_status = result.get("status_code")
        status, error = (
            ("accepted", None)
            if http_status == 202
            else ("uncertain", "unexpected_response")
        )
        response = result.get("response")
        request_id = None
        if isinstance(response, dict):
            try:
                request_id = str(UUID(str(response.get("requestId"))))
            except (TypeError, ValueError, AttributeError):
                pass
    except IfoodClientError as exc:
        http_status, request_id = exc.status_code, None
        status = "error" if http_status and 400 <= http_status < 500 else "uncertain"
        error = (
            "rate_limited"
            if http_status == 429
            else "provider_rejected"
            if status == "error"
            else "transport_uncertain"
        )
    except Exception:
        # Nunca persistir texto arbitrario/credenciais da resposta ou excecao.
        http_status, request_id, status, error = (
            None,
            None,
            "uncertain",
            "transport_uncertain",
        )
    # Nao reaproveitar objetos expirados como fonte de estoque apos o commit.
    # O resultado pertence somente aos IDs originais; o proximo tick recalcula
    # qualquer venda/reposicao que tenha ocorrido durante a rede.
    sync_rls_tenant(db, scope[0])
    row = (
        db.query(Submission)
        .filter(
            Submission.tenant_id == scope[0],
            Submission.request_key == request_key,
            Submission.merchant_id == scope[1],
        )
        .populate_existing()
        .one()
    )
    state = (
        db.query(State)
        .filter(
            State.tenant_id == scope[0],
            State.link_id == row.link_id,
            State.merchant_id == scope[1],
        )
        .populate_existing()
        .with_for_update()
        .one()
    )
    if state.last_request_key != request_key or row.status != "sending":
        db.rollback()
        return {"status": "uncertain", "reason": "attempt_identity_changed"}
    row.status, row.http_status, row.error_code = status, http_status, error
    row.provider_request_id, row.finished_at = request_id, now
    if status == "accepted":
        state.last_accepted_stock, state.status, state.failure_count = (
            sent_stock,
            "accepted",
            0,
        )
        state.reference_source = "api_acceptance"
    else:
        state.failure_count += 1
        state.status = (
            "backoff"
            if http_status == 429
            else "blocked"
            if status == "error"
            else "uncertain"
        )
    state.error_code = error
    result = {
        "status": state.status,
        "desired_stock": state.desired_stock,
        "sent_stock": sent_stock,
        "request_key": request_key,
        "http_status": http_status,
    }
    db.commit()
    return result


def poll_ifood_stock_once(*, client_factory=None, session_factory=None, now=None):
    reason = settings_reason()
    if reason:
        return {"status": "disabled", "reason": reason}
    scope = _scope()
    now = _utc(now or datetime.now(timezone.utc))
    with tenant_context(scope[0]):
        db = (session_factory or SessionLocal)()
        try:
            sync_rls_tenant(db, scope[0])
            target, result = _observe(db, scope, now)
            if result is not None:
                return result
            # Segunda leitura em transacao nova: nao despachar snapshot/identity
            # map anterior ao commit, nem o saldo observado no tick anterior.
            db.commit()
            db.expire_all()
            sync_rls_tenant(db, scope[0])
            if settings_reason() is not None or _scope() != scope:
                return {"status": "blocked", "reason": "scope_changed"}
            target, result = _observe(db, scope, now)
            if result is not None:
                return result
            return _dispatch(db, target, scope, now, client_factory or _client)
        except Exception:
            db.rollback()
            logger.error(
                "[IFOOD] Ciclo de estoque DEV interrompido; nenhuma repeticao cega."
            )
            return {"status": "blocked", "reason": "cycle_failed"}
        finally:
            db.close()
