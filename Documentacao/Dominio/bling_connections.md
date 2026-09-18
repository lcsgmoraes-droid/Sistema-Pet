---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bling_connections

Ver [[Tenant]], [[Bling]], [[bling_company_tenant_links]].

## Definição
Conexão OAuth do tenant com o Bling (1 por tenant).

## Confirmado no código
- Modelo: `bling_connection_models.py:22-71` (`BlingConnection`). `UniqueConstraint("tenant_id", ...)`.
- Colunas: `company_id`, `stock_deposit_id`, `status` (default "active"), `expires_at`/`connected_at`/`last_refresh_at`/`renewal_count`/`last_error`.
- ✅ **Credenciais corretamente criptografadas**: `access_token`, `refresh_token`, `oauth_client_secret` são `Text` armazenados criptografados, expostos via `@property`/`@setter` que chamam `encrypt_secret`/`decrypt_secret` (`app.security.tenant_config_crypto`). `oauth_client_id` fica em texto puro (não é secreto).

## Relacionamentos
- `tenant_id` (via `BaseTenantModel`) sem `ForeignKey()` real — FK fantasma padrão do mixin.
- Sem referências de entrada.

## Utilizado por
- `services/bling_connection_service.py` (get/save/refresh), `bling_routes.py` (`/bling/renovar-token`, `/bling/teste-conexao`).

## Não identificado
- Bom exemplo de criptografia de credencial implementada corretamente — contraste com [[stone_configs]].
