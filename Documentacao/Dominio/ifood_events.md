---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ifood_events

Ver [[ifood_orders]].

## Definição
Evento do iFood persistido antes do acknowledgment — garante idempotência mesmo se o ACK falhar.

## Confirmado no código
- Modelo: `ifood_order_models.py:47-70` (`IfoodEvent`). `UniqueConstraint(tenant_id, ifood_event_id)`.
- Colunas: `merchant_id`, `ifood_event_id`, `ifood_order_id` (⚠️ String solta, sem FK real para `ifood_orders`), `code`/`full_code`, `provider_created_at`, `processed_at`, `acknowledged_at`, `processing_error`, `payload`.
- ✅ Padrão correto de idempotência: grava o evento **antes** de chamar `client.acknowledge_events()` no iFood — evita perder evento se o ACK falhar.

## Relacionamentos
- Referencia informalmente [[ifood_orders]] via `ifood_order_id` (sem FK real).

## Utilizado por
- `integrations/ifood/orders.py::process_order_events()` — motor completo do polling: busca eventos, persiste, busca detalhe do pedido só quando necessário, atualiza [[ifood_orders]], só faz ACK dos que persistiram e processaram com sucesso.

## Não identificado
- Nada notável — bom exemplo de padrão de idempotência bem implementado.
