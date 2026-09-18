---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ecommerceai_inbound_events

Ver [[ecommerceai_connections]].

## Definição
Fila de eventos (webhooks) recebidos da plataforma externa EcommerceAI.

## Confirmado no código
- Modelo: `ecommerceai_integration_models.py:99-138` (`EcommerceAIInboundEvent`). `UniqueConstraint(connection_id, event_id)` — idempotência de eventos recebidos.
- `id` usa `BigInteger().with_variant(Integer, "sqlite")` — padrão de compatibilidade Postgres/SQLite.
- Colunas: `event_type`, `schema_version`, `occurred_at`, `payload` (JSONB), `payload_hash`, `status` (default "received"), `processed_result`, `error_message`.

## Relacionamentos
- FK de saída: `connection_id → ecommerceai_connections.id` (CASCADE).
- Sem referências de entrada.

## Utilizado por
- `routes/ecommerceai_integration_routes.py:593` (recepção de webhook, dedupe por `payload_hash`/`(connection_id, event_id)`).

## Não identificado
- Nada notável.
