---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produtos_historico_precos

Ver [[Produto]], [[notas_entrada]], [[estoque_movimentacoes]].

## Definição
Histórico de alteração de preço de custo/venda/margem de um produto, com motivo (entrada de NF-e, manual, promoção, reajuste).

## Confirmado no código
- Modelo: `produtos_compras_models.py:302-338` (`ProdutoHistoricoPreco`).
- Colunas: `preco_custo_anterior`/`novo`, `preco_venda_anterior`/`novo`, `margem_anterior`/`nova`, variações percentuais, `motivo` (nfe_entrada/manual/promocao/reajuste), `referencia` (texto livre).

## Relacionamentos
- FKs de saída: `produto_id → produtos.id`, `nota_entrada_id → notas_entrada.id` (nullable), `user_id → users.id`.
- Sem referências de entrada.

## Utilizado por
- `notas_entrada/processamento_precos.py`/`processamento_routes.py:332-342` (`_atualizar_custo_produto_entrada`, registra o histórico ao processar nota de entrada).
- `notas_entrada/processamento_acoes.py:143` (importado junto com `EstoqueMovimentacao` para checar se a entrada de estoque já foi lançada).

## Não identificado
- Nada notável.
