---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — Mercado Pago

Parte de [[Integracoes]]. Ver [[E-commerce]], [[API-Security]].

## Identificação
- **Finalidade:** checkout e confirmação de pagamento do e-commerce próprio do CorePet.

## Arquivos
`services/mercado_pago_checkout.py`, `services/ecommerce_payment_config.py`, `routes/ecommerce_webhooks.py`, `routes/ecommerce_webhooks_security.py`.

## Comunicação
REST + OAuth2 (authorization code, por tenant — cada loja conecta sua própria conta Mercado Pago) + webhook recebido.

## Autenticação
`MERCADO_PAGO_OAUTH_CLIENT_ID`/`_SECRET`, `MERCADO_PAGO_OAUTH_REDIRECT_URI`, `MERCADO_PAGO_ACCESS_TOKEN`, `MERCADO_PAGO_WEBHOOK_SECRET`, `MERCADO_PAGO_USE_SANDBOX`, `MERCADO_PAGO_WEBHOOK_VALIDATE_SIGNATURE`.

## Webhook
`POST /webhook/mercadopago/{webhook_token}` (token opaco por tenant) e `POST /webhook/mercadopago` — validação de assinatura HMAC do provedor, controlada por flag `MERCADO_PAGO_WEBHOOK_VALIDATE_SIGNATURE`. 🔵 Confirmado.

## Falhas, retry e resiliência
- `requests` com `timeout=20`.
- 🟡 **Sem fila durável de retry** para falha transitória (lacuna já documentada no `docs/CATALOGO_INTEGRACOES.md` pré-existente, confirmada no código).
- **Idempotência**: registro de evento/hash evita processar o mesmo webhook duas vezes.
- 🔵 Boa prática confirmada: após receber o webhook, o backend **reconsulta o pagamento real na API do Mercado Pago** em vez de confiar apenas no payload recebido — mitiga falsificação de webhook mesmo em caso de falha de validação de assinatura.

## Fluxo
```text
Cliente finaliza checkout no e-commerce CorePet
  → redireciona para Mercado Pago
  → pagamento aprovado/recusado
  → webhook chega no CorePet (assinado)
  → CorePet reconsulta status real na API do Mercado Pago
  → Pedido atualizado
```

## Dependências de funcionalidade
[[E-commerce]], [[PDV-Vendas]] (conciliação financeira).

## Não identificado
- ❓ Comportamento exato quando o Mercado Pago está indisponível por período prolongado (sem fila de retry confirmada) — pedido pode ficar "pendente" sem atualização automática até novo webhook.
