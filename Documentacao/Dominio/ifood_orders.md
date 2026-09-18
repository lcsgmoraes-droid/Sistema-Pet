---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ifood_orders

Ver [[ifood_merchant_configs]], [[ifood_events]], [[Venda]], [[vet_procedimentos_consulta]].

## Definição
Espelho local de um pedido do iFood.

## Confirmado no código
- Modelo: `ifood_order_models.py:17-44` (`IfoodOrder`). `UniqueConstraint(tenant_id, ifood_order_id)`.
- Colunas: `merchant_id`, `ifood_order_id`, `display_id`, `status` (default "PLACED"), `order_type`, `order_timing`, `delivered_by`, `total`, `placed_at`, `preparation_start_at`, `last_event_at`, `last_action`/`last_action_at`, `payload` (JSON completo do pedido).
- ⚠️ **Achado importante — padrão "bypass"**: nenhuma FK para `pedidos`/`vendas`/`clientes`/`produtos`. `upsert_ifood_order()` (`integrations/ifood/orders.py:87-142`) só espelha campos do payload — não há criação de [[Venda]]/[[Pedido]], baixa de estoque ou geração financeira. Mesmo padrão de bypass do módulo veterinário ([[vet_procedimentos_consulta]]), diferente do padrão correto usado pelo e-commerce nativo ([[pedidos]]).

## Relacionamentos
- Sem FK real.
- Referenciada informalmente por [[ifood_events]]`.ifood_order_id` (não FK real, coluna solta).

## Utilizado por
- `integrations/ifood/orders.py` (upsert idempotente antes do ACK do evento), `routes/ifood_order_routes.py`.

## Não identificado
- ❓ Não confirmado se existe conversão manual/futura para Venda em algum outro ponto não referenciado por FK — pedido iFood fica isolado como espelho operacional.
