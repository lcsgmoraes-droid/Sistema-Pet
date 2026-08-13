"""Captura central das alteracoes de Produto.preco_custo."""

from __future__ import annotations

import logging

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_PENDING_CHANGES_KEY = "bling_cost_sync_pending_changes"


def _capture_changed_product_costs(session, _flush_context, _instances) -> None:
    if session.info.get("disable_bling_cost_sync_events"):
        return

    from app.produtos_models import Produto

    pending = session.info.setdefault(_PENDING_CHANGES_KEY, {})
    for product in list(session.dirty):
        if not isinstance(product, Produto):
            continue

        state = inspect(product)
        if not state.persistent:
            continue
        history = state.attrs.preco_custo.history
        if not history.has_changes():
            continue

        pending[(str(product.tenant_id), product.id)] = {
            "produto": product,
            "custo_novo": product.preco_custo,
        }


def _enqueue_captured_product_costs(session, _flush_context) -> None:
    pending = session.info.pop(_PENDING_CHANGES_KEY, {})
    if not pending or session.info.get("disable_bling_cost_sync_events"):
        return

    # Import tardio evita ciclo durante o bootstrap dos modelos.
    from app.services.bling_cost_sync_service import BlingCostSyncService

    for change in pending.values():
        product = change["produto"]
        try:
            result = BlingCostSyncService.queue_product_cost_sync(
                session,
                produto_id=product.id,
                custo_novo=change["custo_novo"],
                motivo="alteracao_preco_custo",
                origem="evento_produto",
                produto=product,
                flush=False,
            )
            if result.get("ok"):
                logger.info(
                    "[BLING COST SYNC] Custo enfileirado automaticamente; produto_id=%s",
                    product.id,
                )
        except Exception:
            # A integracao nao pode desfazer uma operacao valida do cadastro local.
            logger.exception(
                "[BLING COST SYNC] Nao foi possivel enfileirar custo; produto_id=%s",
                getattr(product, "id", None),
            )


def _registered_listeners(event_name: str):
    return list(getattr(Session.dispatch, event_name)._clslevel.get(Session, ()))


def register_bling_cost_sync_events_once() -> None:
    """Registra o listener uma unica vez, inclusive apos reload do modulo."""
    listeners = (
        ("before_flush", _capture_changed_product_costs),
        ("after_flush_postexec", _enqueue_captured_product_costs),
    )
    for event_name, hook in listeners:
        for listener in _registered_listeners(event_name):
            same_hook = (
                getattr(listener, "__module__", None) == __name__
                and getattr(listener, "__name__", None) == hook.__name__
            )
            if same_hook and listener is not hook:
                event.remove(Session, event_name, listener)

        if not event.contains(Session, event_name, hook):
            event.listen(Session, event_name, hook)


register_bling_cost_sync_events_once()
