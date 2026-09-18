---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_listas_preco

Ver [[Produto]], [[listas_preco]].

## Definição
Preço específico de um produto dentro de uma [[listas_preco|lista de preços]], com desconto percentual ou em valor.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:338-358` (`ProdutoListaPreco`).
- Colunas: `produto_id`, `lista_preco_id`, `preco`, `desconto_percentual`, `desconto_valor`, `ativo`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id` (CASCADE), `lista_preco_id → listas_preco.id` (CASCADE).
- Referenciada por: `Produto.listas_preco` e `ListaPreco.produtos` (back_populates) — `produtos_catalogo_models.py:387-389`.

## Utilizado por
- Mesmo caso de [[listas_preco]]: só leitura em `ecommerceai_integration_routes.py` e manipulação em `services/produto_merge_service.py:340-353` (dedup ao mesclar produtos).

## Não identificado
- ⚠️ Mesmo alerta de [[listas_preco]]: sem rota de escrita/CRUD localizada.
