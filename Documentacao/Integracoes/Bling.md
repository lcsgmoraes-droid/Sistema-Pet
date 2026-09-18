---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — Bling (ERP/Fiscal)

Parte de [[Integracoes]]. Ver [[Produtos-Estoque]], [[Compras]], [[API-Security]].

## Identificação
- **Fornecedor:** Bling (ERP de terceiros, mercado brasileiro).
- **Finalidade:** sincronização de estoque, pedidos e emissão/consulta de nota fiscal.
- **Confirmado em:** `docs/CATALOGO_INTEGRACOES.md` (fonte pré-existente, validada contra o código) e diretamente no código.

## Arquivos
`bling_integration.py`, `bling_integration_fiscal.py`, `bling_integration_parts/{core,api,catalogo,notas}.py`, `bling_oauth_routes.py`, `bling_routes.py`, `bling_sync_routes.py`, `bling_sync/`, `integracao_bling_pedido_routes.py`, `integracao_bling_pedido_webhook_processor.py`, `services/bling_pedido_webhook_queue_service.py`, `services/bling_webhook_security.py`, worker dedicado `backend/scripts/run_bling_worker.py`.

## Comunicação
REST + OAuth2 (authorization code) + webhook recebido + fila assíncrona de processamento (tabela Postgres, `SELECT FOR UPDATE SKIP LOCKED`).

## Autenticação
Variáveis (nomes apenas): `BLING_CLIENT_ID`, `BLING_CLIENT_SECRET`, `BLING_REDIRECT_URI`, `BLING_ACCESS_TOKEN`, `BLING_REFRESH_TOKEN`, `BLING_WEBHOOK_TENANT_ID`. Renovação automática de token a cada 5h (job in-process, ver [[Arquitetura]]).

## Webhook
`POST /integracoes/bling/pedido` — protegido por `require_bling_webhook_signature`, validando `X-Bling-Signature-256` (HMAC-SHA256). 🔵 Confirmado ativo.

⚠️ Existe um segundo arquivo, `integracao_bling_webhook_routes.py`, com rota `POST /integracoes/bling/webhook` **sem nenhuma validação de assinatura** — mas **confirmado que não está registrado** em `main_routers.py`/`main.py`. Código morto, não exposto hoje. Ver [[Vulnerabilidades]] item 7 — recomendação de remoção por higiene.

## Falhas, retry e resiliência
- `requests` com `timeout=30`.
- Trata `HTTPError`/rate-limit 429 com `Retry-After` (backoff 1–8s, até 5 tentativas).
- Fila de webhook de pedido com retry exponencial configurável (`BLING_PEDIDO_WEBHOOK_MAX_ATTEMPTS`, default 6 tentativas) e fallback síncrono opcional.
- Worker dedicado com heartbeat em arquivo, monitorado via `bling_flow_monitor_models.py`/`bling_flow_monitor_routes.py`.

## Fluxo
```text
Bling (evento de pedido)
  → webhook assinado
  → fila Postgres (bling_pedido_webhook_events)
  → worker/job processa (retry exponencial)
  → atualiza Pedido/Estoque no CorePet
```

Sentido inverso (CorePet → Bling): sincronização de estoque e emissão fiscal via `bling_sync/` e `bling_integration_fiscal.py`, agendada por `BlingSyncScheduler` (flag `BLING_SYNC_SCHEDULER_ENABLED`) e pelo worker dedicado.

## Dependências de funcionalidade
[[Produtos-Estoque]], [[Compras]] (`vendas/bling-*` no menu).

## Não identificado
- ❓ Relação exata entre este fluxo fiscal via Bling e o módulo `intnfe/` próprio do CorePet (se são complementares por canal ou redundantes) — ver [[Arquitetura#Não identificado]].
