---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ecommerce_notify_requests

Ver [[Produto]].

## Definição
Solicitação de "avise-me quando chegar" para produto fora de estoque na loja virtual.

## Confirmado no código
- Modelo: `models.py:730-747` (`EcommerceNotifyRequest`).
- Colunas: `product_id` (⚠️ sem FK), `product_name`, `email`, `notified`/`notified_at`.

## Relacionamentos
- Sem FK de saída real (`product_id` é FK fantasma).
- Sem referências de entrada.

## Utilizado por
- CRUD completo: `routes/ecommerce_notify_routes.py` — criação, consulta de duplicidade, listagem admin, marcação de notificado.

## Não identificado
- Fluxo simples e sem envolvimento de [[pedidos]]/[[Venda]] — `product_id` deveria ser FK real.
