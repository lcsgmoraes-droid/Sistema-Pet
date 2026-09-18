---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ecommerce_analytics_events

Ver [[pedidos]], [[Produto]].

## Definição
Evento anônimo do funil da loja virtual (tracking de navegação/conversão), alto volume.

## Confirmado no código
- Modelo: `ecommerce_analytics_models.py:9-40` (`EcommerceAnalyticsEvent`).
- Colunas: `event_name`, `session_id`, `channel` (default "ecommerce"), `path`, `product_id` (⚠️ sem FK), `pedido_id` (⚠️ String sem FK, referência solta a `pedidos.pedido_id`), `value`, `extra_data` (JSONB).
- 3 índices compostos (tenant+event+created, tenant+session+created, tenant+channel+created) — desenhado para consultas analíticas de alto volume.

## Relacionamentos
- Sem FK de saída real (`product_id` e `pedido_id` são ambos fantasmas).

## Utilizado por
- Gravação: `routes/ecommerce_public.py:691` (endpoint público de tracking).
- Leitura: `routes/ecommerce_analytics_routes.py:148-157` (dashboard).

## Não identificado
- FKs fantasmas não impedem uso — tabela de eventos de alto volume tolera integridade referencial mais frouxa por design.
