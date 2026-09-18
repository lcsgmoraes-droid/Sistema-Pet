---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ecommerceai_connections

Ver [[ecommerceai_connection_requests]], [[ecommerceai_inbound_events]].

## Definição
Conexão já aprovada/ativa com a plataforma externa "EcommerceAI" — token de API emitido (só o hash é armazenado).

## Confirmado no código
- Modelo: `ecommerceai_integration_models.py:57-96` (`EcommerceAIConnection`). `Base` puro. `UniqueConstraint(request_id)`, índice `(tenant_id, status)`.
- Colunas: `public_id` (unique), `tenant_id` (UUID, NOT NULL aqui), `status` (default "callback_pending"), `token_hash` (unique), `token_prefix`, `scopes` (JSON), `connected_at`/`revoked_at`/`last_event_at`/`last_catalog_read_at`/`last_error`.

## Relacionamentos
- FK de saída: `request_id → ecommerceai_connection_requests.request_id` (CASCADE).
- Referenciada por: [[ecommerceai_inbound_events]]`.connection_id`.

## Utilizado por
- `routes/ecommerceai_integration_routes.py:441` (criação, após aprovação).

## Não identificado
- Nada notável — padrão de token hasheado (nunca o token puro persistido) é boa prática de segurança.
