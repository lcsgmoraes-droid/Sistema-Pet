---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — idempotency_keys

Ver [[app_notifications]], [[pedidos]].

## Definição
Chave de idempotência genérica para requisições HTTP — evita reprocessar a mesma operação (ex.: webhook duplicado, retry de checkout).

## Confirmado no código
- Modelo: `idempotency_models.py:12-79` (`IdempotencyKey`).
- Colunas: `endpoint`, `chave_idempotencia` (indexado), `request_hash` (SHA256 do body), `status` (processing/completed/failed), `response_status_code`/`response_body`/`error_message`.
- ⚠️ **`user_id` sem FK e semanticamente sobrecarregado**: `Integer` solto que significa três coisas diferentes dependendo do caller — `current_user.id` real (fluxo `@idempotent()`), `0` como sentinela de "processo de sistema/webhook" (`ecommerce_webhooks_sales.py`/`ecommerce_webhooks.py`), ou `pedido.cliente_id` (`ecommerce_checkout.py`). Mesmo campo, três semânticas.
- ⚠️ **Lógica de idempotência duplicada em pelo menos 4 lugares**: o decorator genérico `@idempotent()` (`idempotency.py:113-370`) convive com implementações manuais de "buscar/criar/completar" em `ecommerce_webhooks_sales.py`, `ecommerce_webhooks.py` e `ecommerce_checkout.py`, cada uma reimplementando a mesma lógica em vez de usar o decorator.

## Relacionamentos
- Sem FK real de saída.

## Utilizado por
- `idempotency.py` (decorator `@idempotent()`, caminho genérico).
- Uso manual direto em `routes/ecommerce_webhooks_sales.py` (chave `ecommerce-venda:{pedido_id}`, ver [[pedidos]]), `routes/ecommerce_webhooks.py`, `routes/ecommerce_checkout.py`.

## Não identificado
- Recomenda-se ao time unificar os usos manuais para passar pelo decorator, reduzindo a duplicação de lógica.
