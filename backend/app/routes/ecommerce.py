import json

from fastapi import APIRouter, Request, HTTPException
from jose import jwt, JWTError
from uuid import UUID
from app.domain.events.ecommerce_events import PedidoCriadoEvent
from app.domain.events.dispatcher import event_dispatcher
from app.domain.events.event_trace import get_event_trace
from app.domain.events.event_observability import log_event
from app.db.session import SessionLocal
from app.application.commands.checkout_command import CheckoutCommand
from app.application.checkout_service import CheckoutService
from app.events.event_trace_legacy import (
    get_legacy_trace,
    clear_legacy_trace,
)
from app.config import JWT_SECRET_KEY
from app.auth.core import ALGORITHM

router = APIRouter(prefix="/ecommerce", tags=["ecommerce"])


def _normalize_tenant_uuid(tenant_id: str | None) -> str | None:
    if not tenant_id:
        return None

    try:
        return str(UUID(str(tenant_id).strip()))
    except Exception:
        return None


def _resolve_tenant_id(request: Request) -> str | None:
    """
    Extrai tenant_id do JWT ou header X-Tenant-ID.
    Retorna UUID string normalizado.
    """
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "", 1).strip()
            if token:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
                tenant_id = _normalize_tenant_uuid(payload.get("tenant_id"))
                if tenant_id:
                    return tenant_id

    except JWTError:
        pass

    return _normalize_tenant_uuid(request.headers.get("X-Tenant-ID"))


@router.post("/checkout-test")
def checkout_test():
    """
    Endpoint inicial para validar pipeline ecommerce.
    Não cria pedido real ainda — apenas dispara evento.
    """

    event_dispatcher.publish(
        PedidoCriadoEvent(
            correlation_id="checkout-test-correlation-id",
            pedido_id="TEST-001",
            cliente_id=1,
            total=99.90,
            origem="web",
            items_count=0,
            subtotal_items=0.0,
        )
    )

    return {"status": "PedidoCriadoEvent publicado"}


@router.get("/ping")
def ecommerce_ping():
    """
    Health-check simples do domínio ecommerce.
    Útil para:
    - validar roteamento
    - proxy/reverse proxy
    - app mobile futuro
    - monitoramento
    """
    return {
        "status": "ok",
        "domain": "ecommerce",
        "event_system": "active",
    }


@router.post("/checkout")
async def checkout_real(request: Request):
    tenant_id = _resolve_tenant_id(request)
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="tenant_id obrigatório e deve ser UUID válido (JWT ou X-Tenant-ID)",
        )

    # Parse body payload de forma robusta (independe de Content-Type)
    payload = {}
    try:
        raw_body = await request.body()
        if raw_body:
            payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        payload = {}
    
    db = SessionLocal()

    try:
        items = payload.get("items") or payload.get("itens") or []

        service = CheckoutService(db)

        cliente_id = payload.get("cliente_id", 1)
        origem = payload.get("origem", "web")

        log_event(
            stage="checkout",
            event="PedidoCriadoEvent",
            source="checkout_route"
        )

        command = CheckoutCommand(
            cliente_id=cliente_id,
            origem=origem,
            tenant_id=tenant_id,
            items=items,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )

        try:
            novo_pedido = service.processar_checkout(command)
        except ValueError as e:
            if "Conflito de idempotência" in str(e):
                raise HTTPException(status_code=409, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))

        items_count, subtotal_items = service.calcular_items_metadata(command.items)
        correlation_id = service.gerar_correlation_id()

        # EVENTO NASCE SOMENTE APÓS COMMIT
        event_dispatcher.publish(
            PedidoCriadoEvent(
                correlation_id=correlation_id,
                pedido_id=novo_pedido.pedido_id,
                cliente_id=novo_pedido.cliente_id,
                total=novo_pedido.total,
                origem=novo_pedido.origem,
                tenant_id=novo_pedido.tenant_id,
                items_count=items_count,
                subtotal_items=subtotal_items,
            )
        )

        return {
            "status": "pedido_criado",
            "pedido_id": novo_pedido.pedido_id,
        }

    finally:
        db.close()


@router.get("/dispatcher-map")
def dispatcher_map():
    """
    Debug enterprise:
    mostra handlers ativos no dispatcher domain.
    """

    if hasattr(event_dispatcher, "list_handlers"):
        events_map = event_dispatcher.list_handlers()
        return {
            "total_event_types": len(events_map),
            "events": events_map,
        }

    subscribers = getattr(event_dispatcher, "_subscribers", {})
    if subscribers:
        return {
            "total_event_types": len(subscribers),
            "events": {
                str(k.__name__): [h.__name__ for h in v]
                for k, v in subscribers.items()
            },
        }

    handlers = getattr(event_dispatcher, "_handlers", {})
    return {
        "total_event_types": len(handlers),
        "events": {
            str(k): [h.__name__ for h in v]
            for k, v in handlers.items()
        },
    }


@router.get("/legacy-trace")
def legacy_trace():
    return {
        "total": len(get_legacy_trace()),
        "events": get_legacy_trace(),
    }


@router.post("/legacy-trace-clear")
def clear_legacy():
    clear_legacy_trace()
    return {"status": "cleared"}


@router.get("/flow-snapshot")
def flow_snapshot():
    """
    Snapshot enterprise:
    mostra domain + legacy events juntos.
    """

    domain_events = get_event_trace()
    legacy_events = get_legacy_trace()

    return {
        "domain_total": len(domain_events),
        "legacy_total": len(legacy_events),
        "domain": domain_events,
        "legacy": legacy_events,
    }
