---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bling_pedido_webhook_events

Ver [[pedidos_integrados]].

## Definição
Fila persistente para webhooks de pedidos/NFs do Bling — com retry, lock otimista e deduplicação.

## Confirmado no código
- Modelo: `bling_pedido_webhook_queue_models.py:8-46` (`BlingPedidoWebhookEvent`). `Base` puro (não tenant-scoped — evento pode chegar antes de resolver o tenant, `tenant_id` UUID nullable sem FK).
- Colunas: `dedupe_key` (unique), `event_type`, `pedido_bling_id`; controle de fila: `status` (default "pending"), `attempts`/`max_attempts` (default 6), `next_attempt_at`, `started_at`, `processed_at`, `payload`/`response_payload`/`last_error`.
- Índices para pegar próximos itens a processar (`status, next_attempt_at`), por tenant/status e por pedido/status.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `services/bling_pedido_webhook_queue_service.py` (`_claim_next_event`, lock otimista via `status`/`started_at`), `schedulers/bling_sync_scheduler.py`, `integracao_bling_pedido_routes.py`, `services/ops_dashboard_service.py`.

## Não identificado
- Nada notável — fila outbox/inbox bem implementada, com deduplicação e retry corretos.
