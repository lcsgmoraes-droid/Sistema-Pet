---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_lotes

Ver [[Produto]], [[estoque_movimentacoes]], [[campanha_validade_exclusoes]], [[estoque_validade_bloqueios]], [[Venda]].

## Definição
Lote de um produto com data de validade, usado para controle FIFO de estoque e para as campanhas/bloqueios de validade.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:183-245` (`ProdutoLote`).
- Colunas: `produto_id`, `nome_lote`, `data_fabricacao`/`data_validade`, `deposito`, `quantidade_inicial`/`quantidade_disponivel`/`quantidade_reservada`, `limite_dias` (default 30, usado para alerta), `codigo_agregacao`, `status` (ativo/vencido/bloqueado/esgotado), `ordem_entrada` (timestamp Unix, usado para ordenar o consumo FIFO em vez de `created_at`/`id`), `custo_unitario`.
- ⚠️ Campo morto: `product_variation_id` (linha 197-199) marcado `DEPRECATED: usar produto_id` — variações hoje são `Produto` com `tipo_produto='VARIACAO'`, não uma tabela separada; relationship correspondente está comentado (linhas 224-225).

## Relacionamentos
- FK de saída: `produto_id → produtos.id` (CASCADE) — linha 191.
- Referenciada por: `campanha_validade_exclusoes.lote_id`, `estoque_movimentacoes.lote_id`, `estoque_validade_bloqueios.lote_id` (NOT NULL), `vendas_models.py:386` (`lote_id`).
- Relationship reverso: `Produto.lotes` (back_populates) — `produtos_catalogo_models.py:381-383`.

## Utilizado por
- `estoque/service.py` (`_consumir_lotes_fifo`), `routes/app_mobile_funcionario_estoque_routes.py`, `services/bling_nf/desvinculo.py`, `services/ofertas_estudio_service.py`, `services/validade_campanha_service.py`.

## Não identificado
- ⚠️ Campo `product_variation_id` deprecated mas ainda presente na tabela.
