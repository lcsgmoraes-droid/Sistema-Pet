"""
ORM Guards - protecoes automaticas para operacoes de banco de dados.
"""

from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session


def _normalize_tenant_id(value):
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"[ORM TENANT GUARD] tenant_id invalido para insert multi-tenant: {value!r}"
        ) from exc


def _enforce_tenant_on_new_object(obj):
    from app.base_models import BaseTenantModel
    from app.tenancy.context import get_current_tenant

    if not isinstance(obj, BaseTenantModel):
        return

    current_tenant = _normalize_tenant_id(get_current_tenant())
    object_tenant = _normalize_tenant_id(getattr(obj, "tenant_id", None))
    table_name = getattr(obj, "__tablename__", obj.__class__.__name__)

    if current_tenant is None:
        raise RuntimeError(
            f"[ORM TENANT GUARD] Insert em tabela multi-tenant '{table_name}' "
            "sem tenant_id no contexto. Use get_current_user_and_tenant() antes de gravar."
        )

    if object_tenant is None:
        obj.tenant_id = current_tenant
        return

    if object_tenant != current_tenant:
        raise RuntimeError(
            f"[ORM TENANT GUARD] Insert em tabela multi-tenant '{table_name}' "
            f"com tenant_id diferente do contexto. contexto={current_tenant} objeto={object_tenant}."
        )

    obj.tenant_id = object_tenant


def force_identity_ids(session, flush_context, instances):
    """
    Forca entidades novas a gravarem com ID gerado pelo banco e tenant seguro.

    Tenant usa UUID manual como chave primaria e fica fora da regra de id.
    Objetos que herdam BaseTenantModel precisam do tenant no contexto.
    """
    for obj in session.new:
        if obj.__class__.__name__ != "Tenant" and hasattr(obj, "id"):
            obj.id = None

        _enforce_tenant_on_new_object(obj)


def _registered_listeners(event_name: str):
    return list(getattr(Session.dispatch, event_name)._clslevel.get(Session, ()))


def register_identity_guard_once() -> None:
    """Registra o guard de flush uma unica vez, inclusive apos reload do modulo."""
    for listener in _registered_listeners("before_flush"):
        same_hook = (
            getattr(listener, "__module__", None) == __name__
            and getattr(listener, "__name__", None) == "force_identity_ids"
        )
        if same_hook and listener is not force_identity_ids:
            event.remove(Session, "before_flush", listener)

    if not event.contains(Session, "before_flush", force_identity_ids):
        event.listen(Session, "before_flush", force_identity_ids)


register_identity_guard_once()
