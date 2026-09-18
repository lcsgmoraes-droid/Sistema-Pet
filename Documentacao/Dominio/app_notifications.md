---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — app_notifications

Ver [[Usuario]], [[user_push_devices]], [[idempotency_keys]].

## Definição
Notificação in-app (central de notificações do app do tutor/usuário), ligada ao resultado do push.

## Confirmado no código
- Modelo: `models.py:247-287` (`AppNotification`).
- Colunas: `source`/`kind` (taxonomia livre), `payload` (JSON), `read_at`/`cleared_at`/`delivered_at`/`push_ticket_id`/`push_error`.
- ⚠️ `customer_id` é `Integer` solto sem FK (referencia cliente do e-commerce/app do tutor) — FK fantasma.
- ⚠️ **Esquema de idempotência próprio e paralelo**: `idempotency_key` com `UniqueConstraint(tenant_id, user_id, idempotency_key)` — não reaproveita a tabela genérica [[idempotency_keys]]. Duas soluções de idempotência coexistindo no backend, para propósitos parecidos, sem reuso.

## Relacionamentos
- FK de saída: `user_id → users.id`.
- `customer_id` sem FK real.

## Utilizado por
- `services/app_notifications.py::criar_notificacao_app`/`resolve_customer_app_user_id`, `routes/ecommerce_auth_profiles.py`, `routes/app_mobile_routes.py`.

## Não identificado
- `customer_id` deveria ser FK real e não é.
