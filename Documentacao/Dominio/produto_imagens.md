---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_imagens

Ver [[Produto]].

## Definição
Galeria de imagens de um produto (múltiplas por produto, com uma marcada como principal).

## Confirmado no código
- Modelo: `produtos_estoque_models.py:24-47` (`ProdutoImagem`).
- Colunas: `produto_id`, `url`, `ordem`, `e_principal` (bool), `tamanho`/`largura`/`altura`.
- Property `thumbnail_url` chama `build_product_thumbnail_url` (`services/product_image_storage.py`).

## Relacionamentos
- FK de saída: `produto_id → produtos.id` (CASCADE) — `produtos_estoque_models.py:32`.
- Referenciada por: `Produto.imagens` (back_populates, cascade delete-orphan) — `produtos_catalogo_models.py:378-380`.

## Utilizado por
- `routes/app_mobile_funcionario_produto_imagens.py`.
- `services/bling_product_image_service.py`.

## Não identificado
- Nada notável encontrado.
