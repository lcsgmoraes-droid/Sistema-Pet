---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — rotas_entrega_rastreio_tokens

Ver [[rotas_entrega]], [[oferta_publicacao_tokens]].

## Definição
Índice público cross-tenant: token opaco → rota de entrega. Permite acompanhamento público da entrega sem login/tenant conhecido.

## Confirmado no código
- Modelo: `rotas_entrega_models.py:108-123` (`RotaEntregaRastreioToken`). `Base` puro (não `BaseTenantModel`) — mesmo padrão de [[oferta_publicacao_tokens]].
- PK é o próprio `token` (String(64)); `tenant_id` UUID solto (sem FK real, por design do padrão cross-tenant).
- Explicitamente listada como exceção de RLS/tenancy em `tenancy/rls_no_debt.py:22` e `tenancy/filters.py:55`.

## Relacionamentos
- FK de saída: `rota_id → rotas_entrega.id` (CASCADE, unique — 1:1 com a rota).
- Sem referências de entrada.

## Utilizado por
- `rotas_entrega_tracking.py::registrar_token_rastreio()` (upsert por `rota_id`).
- Endpoint público `GET /rotas-entrega/rastreio/{token}` (`rotas_entrega_public_routes.py`), `app_mobile_rastreio_routes.py`, `routes/ecommerce_entregador.py`.

## Não identificado
- Nada notável — padrão consistente com [[oferta_publicacao_tokens]] e devidamente listado como exceção de tenancy no código.
