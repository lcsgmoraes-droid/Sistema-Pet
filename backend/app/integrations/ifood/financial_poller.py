"""Busca Financial somente para a ponte allowlisted do piloto DEV.

Usa o scheduler e o processo lider existentes, sem rede em GET nem operacoes de
catalogo/pedidos. O backoff de falhas pertence ao processo; apos reinicio, o
snapshot mais recente ainda limita a frequencia de consultas bem-sucedidas.
"""

import calendar
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import logging
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select, text

from app.config import settings
from app.db import SessionLocal
from app.ifood_financial_cost_models import IfoodFinancialSaleLink
from app.ifood_financial_models import IfoodFinancialSnapshot
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodOrder, IfoodPdvBridge
from app.models import User
from app.produtos_models import Produto
from app.tenancy.context import get_current_tenant, tenant_context
from app.tenancy.rls import sync_rls_tenant
from app.vendas_models import Venda, VendaItem

from .client import IfoodClientError
from .financial import (
    MODE,
    SOURCE,
    IfoodFinancialError,
    _parse_pages,
    import_financial_pages,
)
from .financial_client import IfoodFinancialClient
from .pdv_pilot import PILOT_SKU, _validated_pilot_values, pilot_settings_reason

logger = logging.getLogger(__name__)
MIN_INTERVAL_SECONDS = 900
MAX_BACKOFF_SECONDS = 6 * 60 * 60
MAX_LOOKBACK_DAYS = 32
JOB_ID = "ifood_financial_dev_pilot"
_retry_state = {}


def _interval():
    return max(
        MIN_INTERVAL_SECONDS, int(settings.IFOOD_FINANCIAL_POLLING_INTERVAL_SECONDS)
    )


def _enabled():
    return (
        bool(settings.IFOOD_FINANCIAL_READ_ENABLED)
        and bool(settings.IFOOD_FINANCIAL_POLLING_ENABLED)
        and pilot_settings_reason() is None
        and bool(str(settings.IFOOD_CLIENT_ID or "").strip())
        and bool(str(settings.IFOOD_CLIENT_SECRET or "").strip())
    )


def register_financial_poll_job(scheduler):
    """Nao cria scheduler/thread nem executa consulta imediatamente ao iniciar."""
    if not _enabled():
        return False
    scheduler.add_job(
        poll_ifood_financial_once,
        "interval",
        seconds=_interval(),
        id=JOB_ID,
        name="iFood Financial: piloto DEV",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        misfire_grace_time=60,
    )
    return True


def _utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def _advisory_lock(db, tenant, merchant):
    if db.get_bind().dialect.name != "postgresql":
        return True
    # Chave estavel e transacional; nao bloqueia vendas/estoque. A rede e limitada
    # pelo cliente Financial (ate 60s de paginacao e timeout por requisicao).
    key = int.from_bytes(
        sha256(f"ifood-financial:{tenant}:{merchant}:{MODE}".encode()).digest()[:8],
        "big",
        signed=True,
    )
    return bool(
        db.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}
        ).scalar()
    )


def _pilot_target(db, tenant, merchant, order_id):
    """Ponte canonica, payload conferido e conjunto exato de itens do piloto."""
    if str(get_current_tenant()) != str(tenant):
        raise IfoodFinancialError("Contexto de empresa divergente.", status_code=403)
    config = db.execute(
        select(IfoodMerchantConfig.id).where(
            IfoodMerchantConfig.tenant_id == tenant,
            IfoodMerchantConfig.merchant_id == merchant,
        )
    ).scalar_one_or_none()
    if config is None:
        return None
    order = (
        db.execute(
            select(IfoodOrder.__table__).where(
                IfoodOrder.tenant_id == tenant,
                IfoodOrder.merchant_id == merchant,
                IfoodOrder.ifood_order_id == order_id,
            )
        )
        .mappings()
        .one_or_none()
    )
    bridge = (
        db.execute(
            select(IfoodPdvBridge.__table__).where(
                IfoodPdvBridge.tenant_id == tenant,
                IfoodPdvBridge.merchant_id == merchant,
                IfoodPdvBridge.ifood_order_id == order_id,
                IfoodPdvBridge.status == "sold",
                IfoodPdvBridge.stock_decreased_at.is_not(None),
            )
        )
        .mappings()
        .one_or_none()
    )
    if order is None or bridge is None:
        return None
    values = _validated_pilot_values(SimpleNamespace(**order))
    if values["evidence_hash"] != bridge["evidence_hash"]:
        raise IfoodFinancialError(
            "A ponte diverge do pedido conferido.", status_code=409
        )
    actor = db.execute(
        select(User.id).where(User.tenant_id == tenant, User.id == bridge["actor_id"])
    ).scalar_one_or_none()
    sale = db.execute(
        select(Venda.data_venda).where(
            Venda.tenant_id == tenant,
            Venda.id == bridge["sale_id"],
            Venda.canal == "ifood",
            Venda.status == "finalizada",
            Venda.data_cancelamento.is_(None),
            Venda.cancelada_por.is_(None),
        )
    ).one_or_none()
    items = list(
        db.execute(
            select(
                VendaItem.produto_id,
                VendaItem.quantidade,
                VendaItem.tipo,
                Produto.codigo,
            )
            .outerjoin(
                Produto,
                (Produto.tenant_id == VendaItem.tenant_id)
                & (Produto.id == VendaItem.produto_id),
            )
            .where(
                VendaItem.tenant_id == tenant, VendaItem.venda_id == bridge["sale_id"]
            )
        )
    )
    if (
        actor is None
        or sale is None
        or len(items) != 1
        or items[0].produto_id != bridge["product_id"]
        or items[0].codigo != PILOT_SKU
        or items[0].quantidade != 1
        or items[0].tipo != "produto"
        or bridge["quantity"] != 1
        or bridge["unit_price"] != values["price"]
    ):
        return None
    links = list(
        db.execute(
            select(IfoodFinancialSaleLink.__table__).where(
                IfoodFinancialSaleLink.tenant_id == tenant,
                IfoodFinancialSaleLink.mode == MODE,
                or_(
                    IfoodFinancialSaleLink.venda_id == bridge["sale_id"],
                    (IfoodFinancialSaleLink.order_id == order_id)
                    & (IfoodFinancialSaleLink.merchant_id == merchant),
                ),
            )
        ).mappings()
    )
    if any(
        link["merchant_id"] != merchant
        or link["order_id"] != order_id
        or link["venda_id"] != bridge["sale_id"]
        for link in links
    ):
        raise IfoodFinancialError("Vinculos financeiros conflitantes.", status_code=409)
    placed_at = order["placed_at"] or sale.data_venda
    return {"date": _utc(placed_at).date(), "actor_id": actor}


def _window(db, tenant, merchant, target_date, now):
    today = now.date()
    if not today - timedelta(days=MAX_LOOKBACK_DAYS) <= target_date <= today:
        raise IfoodFinancialError(
            "Pedido fora da janela recente do piloto.", status_code=409
        )
    month_begin = target_date.replace(day=1)
    month_end = date(
        target_date.year,
        target_date.month,
        calendar.monthrange(target_date.year, target_date.month)[1],
    )
    overlapping = list(
        db.query(IfoodFinancialSnapshot).filter(
            IfoodFinancialSnapshot.tenant_id == tenant,
            IfoodFinancialSnapshot.merchant_id == merchant,
            IfoodFinancialSnapshot.mode == MODE,
            IfoodFinancialSnapshot.active.is_(True),
            IfoodFinancialSnapshot.begin_date <= month_end,
            IfoodFinancialSnapshot.end_date >= month_begin,
        )
    )
    snapshots = [
        row for row in overlapping if row.begin_date <= target_date <= row.end_date
    ]
    if len(snapshots) > 1 or (overlapping and not snapshots):
        raise IfoodFinancialError("Janelas financeiras conflitantes.", status_code=409)
    current = snapshots[0] if snapshots else None
    # Janela fixa permite chegada tardia dentro da competencia sem tentar
    # ampliar diariamente uma janela ja importada (isso geraria sobreposicao).
    begin = current.begin_date if current else month_begin
    end = current.end_date if current else month_end
    if current and any(
        row.id != current.id and row.begin_date <= end and row.end_date >= begin
        for row in overlapping
    ):
        raise IfoodFinancialError("Janelas financeiras conflitantes.", status_code=409)
    if (
        begin < target_date - timedelta(days=32)
        or end > target_date + timedelta(days=32)
        or end < begin
        or (end - begin).days > 32
    ):
        raise IfoodFinancialError(
            "Janela financeira fora dos limites do piloto.", status_code=409
        )
    return begin, end, current


def _remember(key, now, *, failure):
    failures = _retry_state.get(key, {}).get("failures", 0) + 1 if failure else 0
    delay = min(MAX_BACKOFF_SECONDS, _interval() * (2 ** min(failures, 5)))
    _retry_state.clear()  # Um unico pedido allowlisted; nunca acumula tenants.
    _retry_state[key] = {
        "failures": failures,
        "next_check_at": now + timedelta(seconds=delay),
    }


def poll_ifood_financial_once():
    """Um pedido, uma janela completa, sem ACK, caixa, estoque ou pagamentos."""
    if not _enabled():
        return {"status": "disabled"}
    tenant = UUID(settings.IFOOD_PDV_PILOT_TENANT_ID)
    merchant = str(UUID(settings.IFOOD_PDV_PILOT_MERCHANT_ID))
    order_id = settings.IFOOD_PDV_PILOT_ORDER_ID.strip()
    # Orders usa UUID tecnico; nunca display_id/numero da venda como chave remota.
    try:
        order_id = str(UUID(order_id))
    except (TypeError, ValueError, AttributeError):
        return {"status": "blocked"}
    now = datetime.now(timezone.utc)
    key = (str(tenant), merchant, order_id)
    if now < _retry_state.get(key, {}).get("next_check_at", now):
        return {"status": "backoff"}
    with tenant_context(tenant):
        db = SessionLocal()
        try:
            sync_rls_tenant(db, tenant)
            if not _advisory_lock(db, tenant, merchant):
                return {"status": "busy"}
            target = _pilot_target(db, tenant, merchant, order_id)
            if target is None:
                _remember(key, now, failure=False)
                return {"status": "no_eligible_bridge"}
            begin, end, current = _window(db, tenant, merchant, target["date"], now)
            if (
                current is not None
                and _utc(current.created_at) + timedelta(seconds=_interval()) > now
            ):
                _remember(key, now, failure=False)
                return {"status": "recent_snapshot"}
            with IfoodFinancialClient(
                client_id=settings.IFOOD_CLIENT_ID,
                client_secret=settings.IFOOD_CLIENT_SECRET,
                base_url=settings.IFOOD_API_BASE_URL,
                timeout_seconds=min(15, max(1, settings.IFOOD_REQUEST_TIMEOUT_SECONDS)),
            ) as client:
                pages = client.fetch_financial_pages(merchant, begin, end)
            evidence = _parse_pages(pages, merchant, begin, end)
            digest = sha256(
                json.dumps(
                    evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True
                ).encode()
            ).hexdigest()
            refreshed_target = _pilot_target(db, tenant, merchant, order_id)
            new_begin, new_end, new_current = _window(
                db, tenant, merchant, target["date"], now
            )
            if (
                not _enabled()
                or settings.IFOOD_PDV_PILOT_TENANT_ID != str(tenant)
                or settings.IFOOD_PDV_PILOT_MERCHANT_ID != merchant
                or settings.IFOOD_PDV_PILOT_ORDER_ID.strip() != order_id
                or refreshed_target != target
                or (new_begin, new_end) != (begin, end)
                or (new_current.id if new_current else None)
                != (current.id if current else None)
            ):
                raise IfoodFinancialError(
                    "O escopo mudou durante a consulta.", status_code=409
                )
            if (
                current is not None
                and current.source == SOURCE
                and current.payload_hash == digest
            ):
                _remember(key, now, failure=False)
                return {"status": "unchanged"}
            import_financial_pages(
                db,
                tenant,
                merchant,
                begin,
                end,
                pages,
                target["actor_id"],
                mode=MODE,
                source=SOURCE,
            )
            db.commit()
            _remember(key, now, failure=False)
            return {"status": "imported"}
        except (IfoodClientError, IfoodFinancialError, HTTPException) as exc:
            db.rollback()
            _remember(key, now, failure=True)
            code = getattr(exc, "status_code", None)
            logger.warning(
                "[IFOOD] Consulta Financial DEV adiada; codigo=%s, evidencia anterior preservada.",
                code,
            )
            return {"status": "deferred", "status_code": code}
        except Exception:
            db.rollback()
            _remember(key, now, failure=True)
            logger.error(
                "[IFOOD] Consulta Financial DEV adiada por falha local; evidencia anterior preservada."
            )
            return {"status": "deferred"}
        finally:
            db.close()
