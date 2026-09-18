---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — Asaas (billing do próprio SaaS)

Parte de [[Integracoes]]. Diferente de todas as outras integrações listadas: esta **não** serve a operação do pet shop cliente, e sim a **cobrança das assinaturas do próprio CorePet como SaaS** (mensalidade paga pelo tenant à CorePet).

## Identificação
- **Finalidade:** cobrança de assinatura da plataforma (planos/módulos contratados pelo tenant).

## Arquivos
`services/asaas_billing_service.py`, `routes/asaas_billing_routes.py`, `billing_models.py` (`BillingWebhookEvent`, `BillingContractAcceptance`, `BillingOffer`).

## Comunicação
REST + webhook recebido (`POST /webhook` sob o router de billing).

## Autenticação
`ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN`.

## Webhook
Confirmado existir e validado por token; profundidade da validação (assinatura vs. só token estático) não auditada linha a linha nesta rodada. ❓ Necessita validação adicional.

## Falhas, retry e resiliência
- Timeout de 20s.
- 🟡 Sem retry durável confirmado para falha transitória.

## Fluxo
```text
CorePet (plataforma) cobra tenant via Asaas
  → Asaas processa pagamento da mensalidade
  → webhook confirma status
  → AssinaturaModulo/BillingContractAcceptance atualizados
```

## Dependências de funcionalidade
Modelo comercial de módulos contratáveis (ver [[Arquitetura#Módulos ligáveis por tenant]]), painel `/ops` (plataforma).

## Não identificado
- ❓ Profundidade da validação do webhook (assinatura criptográfica vs. token estático).
