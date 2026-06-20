# Historico de Compras Cliente Canais Notificacoes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cliente ve historico unificado por `Cliente.user_id` no ecommerce e app mobile, com canal claro e notificacoes push para compra/status.

**Architecture:** Criar um read model backend em `customer_order_history.py` para agregar `pedidos` e `vendas`, mantendo `/checkout/pedidos` como contrato dos clientes. Criar `order_push_notifications.py` para disparar push sem bloquear checkout, webhook ou operacao de ERP/entrega. Atualizar web/app apenas para exibir `canal_label` e navegar para pedidos ao tocar push de pedido.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, React/Vite, React Native/Expo, Expo Push API, scripts Node de contrato.

---

## File Structure

- Create `backend/app/services/customer_order_history.py`: labels de canal, serializacao de itens, agregacao e deduplicacao do historico.
- Create `backend/app/services/order_push_notifications.py`: montagem e envio tolerante de push de eventos de pedido.
- Create `backend/tests/unit/test_customer_order_history_service.py`: testes unitarios do read model.
- Create `backend/tests/unit/test_order_push_notifications_service.py`: testes unitarios do servico de push.
- Modify `backend/app/routes/ecommerce_checkout.py`: usar read model em `/checkout/pedidos` e notificar checkout criado.
- Modify `backend/app/routes/ecommerce_webhooks.py`: notificar mudancas de pagamento vindas de webhook.
- Modify `backend/app/vendas_routes.py`: notificar pronto para retirada e entregue/retirado.
- Modify `backend/app/api/endpoints/rotas_entrega.py`: notificar saiu para entrega e entrega concluida.
- Modify `backend/tests/unit/test_app_mobile_checkout_contract.py`: contratos de app para canal e push de pedido.
- Modify `frontend/src/pages/ecommerce/EcommerceOrdersPage.jsx`: exibir canal claro no card.
- Modify `frontend/scripts/test-ecommerce-orders-followup.mjs`: contrato web para `canal_label` sem criar script novo.
- Modify `app-mobile/src/types/index.ts`: adicionar `canal` e `canal_label` ao tipo `Pedido`.
- Modify `app-mobile/src/screens/orders/OrdersScreen.tsx`: exibir canal claro no card.
- Modify `app-mobile/src/hooks/usePushNotifications.ts`: navegar para `Pedidos` quando `source === "order"`.

---

### Task 1: Backend Read Model de Historico

**Files:**
- Create: `backend/app/services/customer_order_history.py`
- Create: `backend/tests/unit/test_customer_order_history_service.py`
- Modify: `backend/app/routes/ecommerce_checkout.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_customer_order_history_service.py` with:

```python
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.customer_order_history import (
    build_checkout_history_entry,
    build_sale_history_entry,
    channel_label_for,
    merge_history_entries,
)


def _dt(minutes: int):
    return datetime(2026, 6, 20, 16, 0, 0) + timedelta(minutes=minutes)


def test_channel_label_for_explicit_customer_channels():
    assert channel_label_for("ecommerce") == "Ecommerce"
    assert channel_label_for("app") == "App mobile"
    assert channel_label_for("loja_fisica") == "Loja fisica / ERP"
    assert channel_label_for("mercado_livre") == "Mercado Livre"
    assert channel_label_for("canal_novo") == "Canal novo"


def test_build_checkout_history_entry_preserves_app_channel_and_items():
    pedido = SimpleNamespace(
        pedido_id="PED-APP-1",
        id=10,
        status="pendente",
        total=39.9,
        origem="app",
        created_at=_dt(1),
        tipo_retirada="app_loja",
        palavra_chave_retirada="patinha",
        is_drive=False,
        drive_chegou_at=None,
        drive_entregue_at=None,
    )
    item = SimpleNamespace(
        produto_id=7,
        nome="Racao",
        quantidade=2,
        preco_unitario=10.0,
        subtotal=20.0,
    )

    entry = build_checkout_history_entry(
        pedido,
        [item],
        payment_info={"payment_url": "https://mp.test", "payment_provider": "mercadopago"},
        venda_info={},
    )

    assert entry["historico_id"] == "pedido:PED-APP-1"
    assert entry["origem_tipo"] == "pedido_online"
    assert entry["canal"] == "app"
    assert entry["canal_label"] == "App mobile"
    assert entry["itens"][0]["nome"] == "Racao"
    assert entry["payment_url"] == "https://mp.test"


def test_build_sale_history_entry_uses_erp_channel_and_linked_order_data():
    item = SimpleNamespace(
        produto_id=8,
        produto_nome="Areia",
        servico_descricao=None,
        quantidade=1,
        preco_unitario=25.5,
        subtotal=25.5,
    )
    venda = SimpleNamespace(
        id=123,
        numero_venda="VEN-123",
        status="finalizada",
        status_entrega="pronto",
        canal="loja_fisica",
        total=25.5,
        data_venda=_dt(2),
        created_at=_dt(2),
        itens=[item],
        tem_entrega=False,
        tipo_retirada=None,
        palavra_chave_retirada=None,
        retirado_por=None,
    )
    pedido = SimpleNamespace(
        pedido_id="PED-WEB-9",
        payment_url="https://mp.test",
        payment_provider="mercadopago",
        payment_preference_id="pref-1",
        tipo_retirada="proprio",
        palavra_chave_retirada="coleira",
        is_drive=True,
        drive_chegou_at=None,
        drive_entregue_at=None,
    )

    entry = build_sale_history_entry(venda, linked_order=pedido)

    assert entry["historico_id"] == "venda:123"
    assert entry["origem_tipo"] == "venda"
    assert entry["pedido_id"] == "PED-WEB-9"
    assert entry["canal"] == "loja_fisica"
    assert entry["canal_label"] == "Loja fisica / ERP"
    assert entry["payment_url"] == "https://mp.test"
    assert entry["palavra_chave_retirada"] == "coleira"


def test_merge_history_entries_deduplicates_sale_linked_checkout_order():
    checkout = {
        "historico_id": "pedido:PED-1",
        "origem_tipo": "pedido_online",
        "pedido_id": "PED-1",
        "created_at": _dt(1).isoformat(),
    }
    sale = {
        "historico_id": "venda:9",
        "origem_tipo": "venda",
        "pedido_id": "PED-1",
        "created_at": _dt(3).isoformat(),
    }

    merged = merge_history_entries([checkout], [sale], limit=20)

    assert merged == [sale]
```

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend; python -m pytest tests/unit/test_customer_order_history_service.py -q`

Expected: FAIL with import error for `app.services.customer_order_history`.

- [ ] **Step 3: Implement read model service**

Create `backend/app/services/customer_order_history.py` with the public API used by tests and by the route:

```python
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import joinedload

from app.idempotency_models import IdempotencyKey
from app.models import Cliente
from app.pedido_models import Pedido, PedidoItem
from app.services.sales_channel import normalize_sales_channel
from app.vendas_models import Venda, VendaItem

CHANNEL_LABELS = {
    "ecommerce": "Ecommerce",
    "app": "App mobile",
    "loja_fisica": "Loja fisica / ERP",
    "mercado_livre": "Mercado Livre",
    "shopee": "Shopee",
    "amazon": "Amazon",
}


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else None


def channel_label_for(channel: Any) -> str:
    normalized = normalize_sales_channel(channel, default="ecommerce")
    if normalized in CHANNEL_LABELS:
        return CHANNEL_LABELS[normalized]
    return normalized.replace("_", " ").strip().capitalize() or "Ecommerce"


def _checkout_item_dict(item: Any) -> dict:
    return {
        "produto_id": getattr(item, "produto_id", None),
        "nome": getattr(item, "nome", None) or "Produto",
        "quantidade": _to_float(getattr(item, "quantidade", 0)),
        "preco_unitario": _to_float(getattr(item, "preco_unitario", 0)),
        "subtotal": _to_float(getattr(item, "subtotal", 0)),
    }


def _sale_item_dict(item: Any) -> dict:
    nome = (
        getattr(item, "produto_nome", None)
        or getattr(item, "servico_descricao", None)
        or getattr(getattr(item, "produto", None), "nome", None)
        or "Produto"
    )
    return {
        "produto_id": getattr(item, "produto_id", None),
        "nome": nome,
        "quantidade": _to_float(getattr(item, "quantidade", 0)),
        "preco_unitario": _to_float(getattr(item, "preco_unitario", 0)),
        "subtotal": _to_float(getattr(item, "subtotal", 0)),
    }


def build_checkout_history_entry(
    pedido: Any,
    itens: list[Any],
    *,
    payment_info: dict | None = None,
    venda_info: dict | None = None,
) -> dict:
    payment_info = payment_info or {}
    venda_info = venda_info or {}
    canal = normalize_sales_channel(
        getattr(pedido, "origem", None) or venda_info.get("canal"),
        default="ecommerce",
    )
    pedido_id = getattr(pedido, "pedido_id", None)
    return {
        "historico_id": f"pedido:{pedido_id}",
        "origem_tipo": "pedido_online",
        "pedido_id": pedido_id,
        "venda_id": venda_info.get("venda_id"),
        "numero": pedido_id,
        "status": getattr(pedido, "status", None),
        "status_entrega": venda_info.get("status_entrega"),
        "retirado_por": venda_info.get("retirado_por"),
        "tem_entrega": venda_info.get("tem_entrega"),
        "tipo_retirada": getattr(pedido, "tipo_retirada", None),
        "is_drive": bool(getattr(pedido, "is_drive", False)),
        "drive_chegou_at": _iso(getattr(pedido, "drive_chegou_at", None)),
        "drive_entregue_at": _iso(getattr(pedido, "drive_entregue_at", None)),
        "palavra_chave_retirada": getattr(pedido, "palavra_chave_retirada", None),
        "payment_provider": payment_info.get("payment_provider"),
        "payment_preference_id": payment_info.get("payment_preference_id"),
        "payment_url": payment_info.get("payment_url"),
        "canal": canal,
        "canal_label": channel_label_for(canal),
        "total": _to_float(getattr(pedido, "total", 0)),
        "created_at": _iso(getattr(pedido, "created_at", None)),
        "itens_count": len(itens),
        "itens": [_checkout_item_dict(item) for item in itens],
    }


def build_sale_history_entry(venda: Any, *, linked_order: Any | None = None) -> dict:
    canal = normalize_sales_channel(getattr(venda, "canal", None), default="loja_fisica")
    pedido_id = getattr(linked_order, "pedido_id", None)
    created_at = getattr(venda, "data_venda", None) or getattr(venda, "created_at", None)
    itens = list(getattr(venda, "itens", []) or [])
    return {
        "historico_id": f"venda:{getattr(venda, 'id', None)}",
        "origem_tipo": "venda",
        "pedido_id": pedido_id,
        "venda_id": getattr(venda, "id", None),
        "numero": getattr(venda, "numero_venda", None) or str(getattr(venda, "id", "")),
        "status": getattr(venda, "status", None),
        "status_entrega": getattr(venda, "status_entrega", None),
        "retirado_por": getattr(venda, "retirado_por", None),
        "tem_entrega": bool(getattr(venda, "tem_entrega", False)),
        "tipo_retirada": getattr(venda, "tipo_retirada", None)
        or getattr(linked_order, "tipo_retirada", None),
        "is_drive": bool(getattr(linked_order, "is_drive", False)),
        "drive_chegou_at": _iso(getattr(linked_order, "drive_chegou_at", None)),
        "drive_entregue_at": _iso(getattr(linked_order, "drive_entregue_at", None)),
        "palavra_chave_retirada": getattr(venda, "palavra_chave_retirada", None)
        or getattr(linked_order, "palavra_chave_retirada", None),
        "payment_provider": getattr(linked_order, "payment_provider", None),
        "payment_preference_id": getattr(linked_order, "payment_preference_id", None),
        "payment_url": getattr(linked_order, "payment_url", None),
        "canal": canal,
        "canal_label": channel_label_for(canal),
        "total": _to_float(getattr(venda, "total", 0)),
        "created_at": _iso(created_at),
        "itens_count": len(itens),
        "itens": [_sale_item_dict(item) for item in itens],
    }


def merge_history_entries(
    checkout_entries: list[dict],
    sale_entries: list[dict],
    *,
    limit: int,
) -> list[dict]:
    linked_pedido_ids = {
        entry.get("pedido_id") for entry in sale_entries if entry.get("pedido_id")
    }
    visible_checkout = [
        entry
        for entry in checkout_entries
        if not entry.get("pedido_id") or entry.get("pedido_id") not in linked_pedido_ids
    ]
    merged = [*sale_entries, *visible_checkout]
    merged.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return merged[:limit]
```

Then add the DB-backed `list_customer_order_history()` function in the same file using `Cliente.user_id == user_id`, `Pedido.cliente_id == user_id`, and `Venda.cliente_id.in_(cliente_ids)`.

- [ ] **Step 4: Wire `/checkout/pedidos` to the read model**

In `backend/app/routes/ecommerce_checkout.py`, replace the query/build loop inside `listar_pedidos_cliente()` with:

```python
from app.services.customer_order_history import list_customer_order_history

# inside listar_pedidos_cliente
pedidos = list_customer_order_history(
    db,
    tenant_id=tenant_id,
    user_id=identity.user_id,
    limit=limit,
)
response = {"pedidos": pedidos}
db.rollback()
return response
```

- [ ] **Step 5: Run tests to verify GREEN**

Run: `cd backend; python -m pytest tests/unit/test_customer_order_history_service.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/customer_order_history.py backend/app/routes/ecommerce_checkout.py backend/tests/unit/test_customer_order_history_service.py
git commit -m "feat: agrega historico de compras do cliente"
```

---

### Task 2: Backend Push de Eventos de Pedido

**Files:**
- Create: `backend/app/services/order_push_notifications.py`
- Create: `backend/tests/unit/test_order_push_notifications_service.py`
- Modify: `backend/app/routes/ecommerce_checkout.py`
- Modify: `backend/app/routes/ecommerce_webhooks.py`
- Modify: `backend/app/vendas_routes.py`
- Modify: `backend/app/api/endpoints/rotas_entrega.py`

- [ ] **Step 1: Write the failing push service tests**

Create `backend/tests/unit/test_order_push_notifications_service.py` with:

```python
from types import SimpleNamespace

from app.services.order_push_notifications import (
    build_order_push_content,
    notify_order_event,
)


class FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *args):
        return self

    def first(self):
        return self.user


class FakeDB:
    def __init__(self, user):
        self.user = user

    def query(self, model):
        return FakeQuery(self.user)


def test_build_order_push_content_maps_payment_and_fulfillment_events():
    approved = build_order_push_content(
        event="payment_approved",
        pedido_id="PED-1",
        venda_id=10,
        canal="ecommerce",
    )
    ready = build_order_push_content(
        event="ready_for_pickup",
        pedido_id="PED-1",
        venda_id=10,
        canal="app",
    )

    assert approved["title"] == "Pagamento aprovado"
    assert approved["data"]["source"] == "order"
    assert approved["data"]["kind"] == "order_status"
    assert approved["data"]["canal"] == "ecommerce"
    assert ready["title"] == "Pedido pronto para retirada"
    assert ready["data"]["canal"] == "app"


def test_notify_order_event_sends_expo_push_without_blocking(monkeypatch):
    calls = []

    def fake_post(url, json, timeout, headers=None):
        calls.append({"url": url, "json": json, "timeout": timeout, "headers": headers})
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"data": {"status": "ok"}})

    monkeypatch.setattr("app.services.order_push_notifications.requests.post", fake_post)
    user = SimpleNamespace(id=5, tenant_id="tenant-1", push_token="ExponentPushToken[test]")

    sent = notify_order_event(
        FakeDB(user),
        tenant_id="tenant-1",
        user_id=5,
        event="checkout_created",
        pedido_id="PED-2",
        venda_id=None,
        canal="app",
    )

    assert sent is True
    assert calls[0]["json"]["to"] == "ExponentPushToken[test]"
    assert calls[0]["json"]["data"]["pedido_id"] == "PED-2"


def test_notify_order_event_ignores_missing_token_and_send_errors(monkeypatch):
    def failing_post(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.services.order_push_notifications.requests.post", failing_post)

    assert notify_order_event(FakeDB(SimpleNamespace(push_token=None)), tenant_id="t", user_id=1, event="checkout_created") is False
    assert notify_order_event(
        FakeDB(SimpleNamespace(id=1, tenant_id="t", push_token="ExponentPushToken[test]")),
        tenant_id="t",
        user_id=1,
        event="checkout_created",
    ) is False
```

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend; python -m pytest tests/unit/test_order_push_notifications_service.py -q`

Expected: FAIL with import error for `app.services.order_push_notifications`.

- [ ] **Step 3: Implement push service**

Create `backend/app/services/order_push_notifications.py` with `build_order_push_content()` and `notify_order_event()`. It must query `User`, skip missing token, call `https://exp.host/--/api/v2/push/send`, catch exceptions, and return `True` only when a request was attempted successfully.

- [ ] **Step 4: Wire event calls**

Add non-blocking calls:

```python
notify_order_event(db, tenant_id=tenant_id, user_id=pedido.cliente_id, event="checkout_created", pedido_id=pedido.pedido_id, canal=pedido.origem)
notify_order_event(db, tenant_id=tenant_id, user_id=pedido.cliente_id, event="payment_approved", pedido_id=pedido.pedido_id, venda_id=venda_id, canal=pedido.origem)
notify_order_event(db, tenant_id=tenant_id, user_id=cliente.user_id, event="ready_for_pickup", venda_id=venda.id, canal=venda.canal)
notify_order_event(db, tenant_id=tenant_id, user_id=cliente.user_id, event="out_for_delivery", venda_id=venda.id, canal=venda.canal)
notify_order_event(db, tenant_id=tenant_id, user_id=cliente.user_id, event="delivered", venda_id=venda.id, canal=venda.canal)
```

Each call must run after the local status change and must not abort the route.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `cd backend; python -m pytest tests/unit/test_order_push_notifications_service.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/order_push_notifications.py backend/app/routes/ecommerce_checkout.py backend/app/routes/ecommerce_webhooks.py backend/app/vendas_routes.py backend/app/api/endpoints/rotas_entrega.py backend/tests/unit/test_order_push_notifications_service.py
git commit -m "feat: notifica eventos de pedido no app"
```

---

### Task 3: Contratos Backend de Rotas e Integracao

**Files:**
- Create: `backend/tests/unit/test_customer_order_history_route_contract.py`
- Modify: `backend/tests/unit/test_mercado_pago_checkout_contract.py`
- Modify: `backend/tests/unit/test_app_mobile_checkout_contract.py`

- [ ] **Step 1: Write failing route contract tests**

Create `backend/tests/unit/test_customer_order_history_route_contract.py` with:

```python
import inspect

from app.routes import ecommerce_checkout, ecommerce_webhooks
from app.services import customer_order_history


def test_checkout_pedidos_route_uses_customer_order_history_service():
    source = inspect.getsource(ecommerce_checkout.listar_pedidos_cliente)

    assert "list_customer_order_history" in source
    assert "user_id=identity.user_id" in source
    assert "tenant_id=tenant_id" in source


def test_customer_order_history_queries_only_cliente_user_id_scope():
    source = inspect.getsource(customer_order_history.list_customer_order_history)

    assert "Cliente.user_id == user_id" in source
    assert "Pedido.cliente_id == user_id" in source
    assert "Venda.cliente_id.in_(cliente_ids)" in source
    assert "Venda.tenant_id == tenant_id" in source


def test_webhook_payment_status_triggers_order_push():
    source = inspect.getsource(ecommerce_webhooks.webhook_mercadopago_tenant)

    assert "notify_order_event" in source
    assert "payment_approved" in source
    assert "payment_in_analysis" in source
    assert "payment_failed" in source
```

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend; python -m pytest tests/unit/test_customer_order_history_route_contract.py -q`

Expected: FAIL until routes/service contain the required calls.

- [ ] **Step 3: Implement missing route calls**

Finish wiring after Task 1 and Task 2 until the contract tests pass.

- [ ] **Step 4: Extend mobile contract test**

In `backend/tests/unit/test_app_mobile_checkout_contract.py`, add:

```python
def test_mobile_orders_screen_shows_channel_label_and_order_push_navigates_to_orders():
    orders = _read_mobile_source("app-mobile/src/screens/orders/OrdersScreen.tsx")
    hook = _read_mobile_source("app-mobile/src/hooks/usePushNotifications.ts")
    types = _read_mobile_source("app-mobile/src/types/index.ts")

    assert "canal_label" in types
    assert "canal_label" in orders
    assert "App mobile" in orders
    assert 'data.source === "order"' in hook
    assert 'navigateWhenReady("Pedidos"' in hook
```

- [ ] **Step 5: Run backend contracts**

Run: `cd backend; python -m pytest tests/unit/test_customer_order_history_route_contract.py tests/unit/test_app_mobile_checkout_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/tests/unit/test_customer_order_history_route_contract.py backend/tests/unit/test_app_mobile_checkout_contract.py backend/tests/unit/test_mercado_pago_checkout_contract.py
git commit -m "test: cobre contratos do historico e notificacoes"
```

---

### Task 4: UI Web e App Mobile

**Files:**
- Modify: `frontend/src/pages/ecommerce/EcommerceOrdersPage.jsx`
- Modify: `frontend/scripts/test-ecommerce-orders-followup.mjs`
- Modify: `app-mobile/src/types/index.ts`
- Modify: `app-mobile/src/screens/orders/OrdersScreen.tsx`
- Modify: `app-mobile/src/hooks/usePushNotifications.ts`

- [ ] **Step 1: Write failing frontend/mobile contract assertions**

In `frontend/scripts/test-ecommerce-orders-followup.mjs`, add assertions that the ecommerce order card uses `canal_label` and fallback labels:

```js
assertContains(source, "order.canal_label");
assertContains(source, "getOrderChannelLabel");
assertContains(source, "App mobile");
assertContains(source, "Loja fisica / ERP");
```

In `backend/tests/unit/test_app_mobile_checkout_contract.py`, use the test from Task 3 Step 4.

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
cd frontend; npm run test:ecommerce-orders-followup
cd ..\backend; python -m pytest tests/unit/test_app_mobile_checkout_contract.py::test_mobile_orders_screen_shows_channel_label_and_order_push_navigates_to_orders -q
```

Expected: FAIL because UI has not yet rendered channel labels and push hook only handles vet notifications.

- [ ] **Step 3: Implement ecommerce channel display**

Add `getOrderChannelLabel(order)` and display a small channel pill in `EcommerceOrdersPage.jsx` near the order date/status. Use `order.canal_label` first, then map `order.canal`.

- [ ] **Step 4: Implement app mobile channel display and push navigation**

Add `canal?: string | null` and `canal_label?: string | null` to `Pedido`. Add a channel label helper and render a small row/pill in `OrdersScreen.tsx`. In `usePushNotifications.ts`, before vet handling:

```ts
if (data.source === "order") {
  navigateWhenReady("Pedidos");
  return;
}
```

- [ ] **Step 5: Run UI contracts**

Run:

```powershell
cd frontend; npm run test:ecommerce-orders-followup
cd ..\backend; python -m pytest tests/unit/test_app_mobile_checkout_contract.py::test_mobile_orders_screen_shows_channel_label_and_order_push_navigates_to_orders -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/pages/ecommerce/EcommerceOrdersPage.jsx frontend/scripts/test-ecommerce-orders-followup.mjs app-mobile/src/types/index.ts app-mobile/src/screens/orders/OrdersScreen.tsx app-mobile/src/hooks/usePushNotifications.ts backend/tests/unit/test_app_mobile_checkout_contract.py
git commit -m "feat: mostra canal no historico do cliente"
```

---

### Task 5: Verification and Finish

**Files:**
- Modify only files touched by previous tasks if verification exposes failures.

- [ ] **Step 1: Run focused backend tests**

Run:

```powershell
cd backend
python -m pytest tests/unit/test_customer_order_history_service.py tests/unit/test_order_push_notifications_service.py tests/unit/test_customer_order_history_route_contract.py tests/unit/test_app_mobile_checkout_contract.py tests/unit/test_mercado_pago_checkout_contract.py -q
```

Expected: PASS.

- [ ] **Step 2: Run focused frontend tests**

Run:

```powershell
cd frontend
npm run test:ecommerce-orders-followup
npm run test:ecommerce-payment-return-flow
```

Expected: PASS.

- [ ] **Step 3: Run build/lint checks**

Run:

```powershell
cd frontend
npm run lint:core -- --quiet
npm run build
cd ..\app-mobile
npm run typecheck
```

Expected: PASS.

- [ ] **Step 4: Run release safety check**

Run:

```powershell
cd C:\Users\lcs_g\Sistema-Pet
.\FLUXO_UNICO.bat release-check
```

Expected: PASS.

- [ ] **Step 5: Finish task branch**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "Adiciona historico de compras por canal e notificacoes" -Push
```

Expected: branch pushed and PR instructions/output available.

## Self-Review

- Spec coverage: history by `Cliente.user_id`, explicit channel labels, pending checkout orders, consolidated sales, push events, web/app display, and mobile navigation are covered by Tasks 1-4.
- Placeholder scan: no TODO/TBD placeholders are present; each task has concrete file paths, commands, and expected outcomes.
- Type consistency: response fields stay consistent across plan: `historico_id`, `origem_tipo`, `pedido_id`, `venda_id`, `canal`, `canal_label`, `status`, `status_entrega`, `total`, `created_at`, `itens`.
