---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ecommerce_payment_gateway_configs

Ver [[Tenant]].

## Definição
Credenciais OAuth do gateway de pagamento (Mercado Pago) por tenant, para a loja virtual.

## Confirmado no código
- Modelo: `ecommerce_payment_models.py:8-37` (`EcommercePaymentGatewayConfig`). `UniqueConstraint(tenant_id, provider)`.
- Colunas: `provider` (default "mercadopago"), `enabled`, `environment`, `public_key`, `access_token_encrypted`, `refresh_token_encrypted`, `webhook_secret_encrypted`, `oauth_client_id`/`oauth_client_secret_encrypted`, `webhook_token` (unique), `oauth_connected`, `mercado_pago_user_id`.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `routes/ecommerce_payment_config_routes.py` (criação/gestão), `services/ecommerce_payment_config.py` (fluxo OAuth/webhook).

## Não identificado
- ❓ Campos `*_encrypted` sugerem criptografia na camada de serviço (sem `EncryptedType` no model) — não confirmado se a criptografia de fato ocorre antes do INSERT/UPDATE.
