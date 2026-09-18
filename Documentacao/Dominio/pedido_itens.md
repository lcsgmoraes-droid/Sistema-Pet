---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedido_itens

Ver [[pedidos]], [[Produto]].

## Definição
Item de linha de um [[pedidos|pedido]] de e-commerce.

## Confirmado no código
- Modelo: `pedido_models.py:152-172` (`PedidoItem`).
- Colunas: `nome`, `quantidade`, `preco_unitario`, `subtotal`.
- ⚠️ `produto_id` é `Integer` sem `ForeignKey()` — FK fantasma.
- ⚠️ Proteção anti-duplicação em `Pedido.adicionar_item()` busca só em `db.new` (objetos pendentes de flush), não faz `SELECT` contra o banco — se o item já foi persistido em chamada anterior fora da mesma transação, pode duplicar.

## Relacionamentos
- FK de saída: `pedido_id → pedidos.pedido_id`.
- Sem referências de entrada.

## Utilizado por
- Criado via `Pedido.adicionar_item()`; lido em `_integrar_venda_ao_motor()` (`ecommerce_webhooks_sales.py:531`) para montar os itens da Venda gerada.

## Não identificado
- `produto_id` deveria ser FK real e não é.
- Risco de duplicação em cenário de retry fora da mesma transação.
