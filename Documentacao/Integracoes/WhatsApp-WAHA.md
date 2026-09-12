---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — WhatsApp (WAHA + 360dialog + n8n)

Parte de [[Integracoes]]. Ver [[API-Security]], docs pré-existentes `docs/N8N_WORKFLOW_PILOTO_WHATSAPP.md`, `docs/WHATSAPP_ATENDIMENTO_PREMIUM.md`.

## Identificação
- **Finalidade:** atendimento e vendas via WhatsApp com IA, com handoff para humano.
- **Arquitetura de orquestração:** WAHA (WhatsApp HTTP API self-hosted) + n8n (automação) como camada externa; CorePet expõe uma API interna para essa ponte.

## Arquivos
`whatsapp/sender.py` (clientes 360dialog e WAHA), `whatsapp/webhook.py`, `whatsapp/security.py`, `whatsapp/ai_service.py`, `whatsapp/processor*.py`, `api/whatsapp_orchestrator_internal_routes.py`, `security/tenant_config_crypto.py`, frontend: `frontend/src/stores/whatsappStore.ts` (única store Zustand real do frontend, ver [[Funcionalidades]]).

## Comunicação
REST + webhook recebido (provedor → CorePet) + ponte interna REST protegida (n8n/WAHA → CorePet).

## Autenticação
- Por tenant, criptografado no banco (Fernet, chave mestra `PAYMENT_CONFIG_ENCRYPTION_KEY`).
- Globais: `WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN`, `WHATSAPP_ORCHESTRATOR_WRITE_TOKEN`, `COREPET_WHATSAPP_DATA_BASE_URL`.
- Legado simples: `WHATSAPP_API_URL`/`WHATSAPP_API_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID` no `.env.example` do backend.

## Webhook
`POST /webhook/whatsapp/...` — assinatura HMAC-SHA256 do 360dialog **ou** header customizado `X-CorePet-Webhook-Token`, validado via `hmac.compare_digest` (comparação segura contra timing attack) em `whatsapp/security.py`. 🔵 Confirmado.

`POST /internal/whatsapp-orchestrator/...` — token interno, **fail-closed** se o segredo estiver ausente (recusa em vez de aceitar sem validação).

## Falhas, retry e resiliência
- `httpx.AsyncClient(timeout=30.0)` em todos os clientes (360dialog e WAHA).
- 🟡 **Sem contrato único de fila/retry** para toda a mensageria de saída.
- 🟡 **Sem deduplicação persistente por `wamid`** (ID de mensagem do WhatsApp) — risco de processar a mesma mensagem duas vezes em replay.

## Fluxo
```text
Cliente (WhatsApp) → WAHA/360dialog → webhook CorePet (assinado)
  → whatsapp/processor (IA responde ou aciona handoff humano)
  → n8n orquestra passos externos quando necessário
  → resposta enviada de volta via sender.py
```

## Dependências de funcionalidade
Atendimento ao cliente, potencialmente [[PDV-Vendas]] (vendas iniciadas por chat), [[Campanhas]] (disparo de promoções).

## Não identificado
- ❓ Necessita validação: política de replay/idempotência do lado do provedor (WAHA reenvia webhook em caso de timeout do CorePet?).
