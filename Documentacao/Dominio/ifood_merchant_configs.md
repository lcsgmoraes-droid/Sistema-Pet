---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ifood_merchant_configs

Ver [[Tenant]], [[ifood_orders]].

## Definição
Configuração operacional da integração iFood por tenant (1 por tenant).

## Confirmado no código
- Modelo: `ifood_integration_models.py:17-41` (`IfoodMerchantConfig`). `UniqueConstraint("tenant_id", ...)`.
- ✅ **Sem armazenamento de credenciais na tabela**: docstring explícita diz que as credenciais OAuth do app CorePet "ficam somente nas variáveis de ambiente do servidor" — a tabela só guarda config operacional: `merchant_id`, `active`, `catalog_source` (default "ecommerce"), `default_markup_percent`, `stock_safety`, `status` (default "draft"), timestamps/erros de sync.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `routes/ifood_integration_routes.py` (cria/edita config, atualiza status em conexão/erro), `integrations/ifood/poller.py`, `integrations/ifood/orders.py`.

## Não identificado
- Nada notável — abordagem de não persistir segredo algum na tabela é a mais segura possível.
