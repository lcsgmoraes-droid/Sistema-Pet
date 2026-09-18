---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ecommerceai_connection_requests

Ver [[ecommerceai_connections]], [[Tenant]].

## Definição
Solicitação de conexão (handshake OAuth-like) entre CorePet e a plataforma externa "EcommerceAI".

## Confirmado no código
- Modelo: `ecommerceai_integration_models.py:26-54` (`EcommerceAIConnectionRequest`). `Base` puro (não tenant-scoped — `tenant_id` é opcional aqui, porque a solicitação ainda não tem tenant resolvido).
- Colunas: `request_id`/`request_nonce` (unique), `client_id`, `ecommerceai_user_id`, `account_name`/`account_email`, `callback_url`, `state` (unique), `requested_scopes` (JSON), `status` (default "pending"), `tenant_id` (UUID, nullable), `expires_at`/`approved_at`/`rejected_at`/`callback_error`.

## Relacionamentos
- FK de saída: `approved_by_user_id → users.id`.
- Referenciada por: [[ecommerceai_connections]]`.request_id` (aponta pra coluna `request_id`, não `id`).

## Utilizado por
- `routes/ecommerceai_integration_routes.py:297` (criação).

## Não identificado
- Nada notável.
