---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — funcionario_contagem_itens

Ver [[funcionario_contagens]], [[Produto]].

## Definição
Item de linha de uma [[funcionario_contagens|contagem de estoque]] feita pelo app do funcionário.

## Confirmado no código
- Modelo: `funcionario_contagem_models.py:44-77` (`FuncionarioContagemItem`).
- Colunas: `ordem`, `codigo`/`codigo_barras`/`gtin_ean` (snapshots do produto), `nome`, `unidade` (default "UN"), `quantidade` (Float), `preco_custo_snapshot`/`preco_venda_snapshot` (snapshot de preços no momento da contagem, não vinculado dinamicamente ao produto), `observacao`.

## Relacionamentos
- FKs de saída: `contagem_id → funcionario_contagens.id` (CASCADE), `produto_id → produtos.id`.
- Sem referências de entrada.

## Utilizado por
- `routes/app_mobile_funcionario_contagem_routes.py`.

## Não identificado
- Nada notável.
