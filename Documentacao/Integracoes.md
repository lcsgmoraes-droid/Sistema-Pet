---
tipo: eixo
atualizado: 2026-09-12
---

# Integrações

Um dos 4 grandes eixos. Ver [[README]]. Fonte pré-existente aproveitada e validada contra o código: `docs/CATALOGO_INTEGRACOES.md` (18 integrações catalogadas pelo próprio time, atualizado 2026-09-09) — este documento resume as integrações mais complexas com detalhe adicional confirmado por agente de exploração; para o catálogo completo original, consulte o arquivo citado.

## Integrações com documento próprio

| Integração | Tipo | Doc |
|---|---|---|
| Bling | ERP/fiscal — OAuth2 + webhook + fila | [[Bling]] |
| WhatsApp (WAHA + 360dialog + n8n) | Atendimento — webhook + IA | [[WhatsApp-WAHA]] |
| Mercado Pago | Pagamento e-commerce — OAuth2 + webhook | [[Mercado-Pago]] |
| SEFAZ + IntNFe | Fiscal — certificado A1 + REST | [[Fiscal-IntNFe-SEFAZ]] |
| iFood | Delivery — OAuth2 + polling | [[iFood]] |
| Stone | Conciliação de cartão — **arquivo, não API** | [[Stone]] |
| OpenAI (+ Groq/Google AI) | IA auxiliar | [[OpenAI-IA]] |
| Asaas | Billing do próprio SaaS | [[Asaas]] |

## Outras integrações confirmadas (menor complexidade — sem doc próprio para não criar arquivos desnecessários)

| Integração | Arquivos | Auth | Observação |
|---|---|---|---|
| EcommerceAI | `routes/ecommerceai_integration_routes.py`, `ecommerceai_integration_models.py` | Bootstrap HMAC com nonce/timestamp (`ECOMMERCEAI_INTEGRATION_BOOTSTRAP_SECRET`) | Parceria de catálogo/eventos B2B |
| Pagar.me | `routes/ecommerce_webhooks.py` (`POST /pagarme`) | — | ❓ Webhook legado/condicional; decisão de aposentar ou formalizar ainda pendente |
| E-mail SMTP | `services/email_service.py` | credenciais SMTP | Notificações transacionais |
| Expo Push | `services/order_push_notifications.py` | — | Notificações do app mobile |
| Storage S3-compatível | `services/product_image_storage.py` | credenciais S3 (boto3) | Alternativa ao storage local, ver [[API-Security]] |
| Ops Alert (webhook/e-mail) | `services/ops_alert_notifier.py` | — | Alertas operacionais internos |
| PubMed / DailyMed / VMD | `services/vet_clinical_evidence.py` | — | Evidência clínica veterinária, sync semanal desligado por padrão |
| Google Maps | `services/google_maps_service.py` | `GOOGLE_MAPS_API_KEY` | Geocodificação/rotas para [[Entregas]]; 🟡 sem retry/cache confirmado |

## Não confirmadas / necessitam validação

- **Firebase** (`FIREBASE_SERVER_KEY`, `FIREBASE_PROJECT_ID`) — presente no `.env.example`, sem uso ativo encontrado no backend. ❓ Pode ser legado substituído por Expo Push.
- **Z-API** — citado apenas em comentários/rascunhos segundo `docs/CATALOGO_INTEGRACOES.md`; não é integração executável hoje.

## Padrão geral de risco observado

| Padrão | Integrações que seguem bem | Integrações com lacuna |
|---|---|---|
| Validação de assinatura de webhook | Bling (pedido), Mercado Pago, WhatsApp, EcommerceAI | Bling legado (não exposto), Pagar.me (a confirmar) |
| Retry com backoff | Bling, OpenAI | Mercado Pago, iFood, WhatsApp (saída), Google Maps |
| Reconsulta de estado real após webhook (anti-falsificação) | Mercado Pago | — |
| Timeout configurado | Todas as integrações de rede confirmadas | — |

Ver consolidado de risco em [[Vulnerabilidades]] e [[Matriz-de-Riscos]].

## Relação com funcionalidades

```text
[[PDV-Vendas]] → Stone (conciliação), Mercado Pago, iFood
[[Produtos-Estoque]] → Bling (sync), SEFAZ/IntNFe (nota de entrada)
[[Financeiro]] → Stone, conciliação bancária
[[Veterinario]] → OpenAI (IA clínica), PubMed/DailyMed/VMD
[[E-commerce]] → Mercado Pago, EcommerceAI
Atendimento → WhatsApp/WAHA, OpenAI
```

## Não identificado

- Lista exaustiva de todas as 18 integrações do `docs/CATALOGO_INTEGRACOES.md` não foi recriada aqui integralmente — 8 têm documento próprio, 8 estão resumidas na tabela acima; consulte o catálogo original para as demais.
