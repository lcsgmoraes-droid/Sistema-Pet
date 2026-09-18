---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_sku_aliases

Ver [[Produto]], [[produto_fusao_logs]].

## Definição
Preserva códigos SKU antigos/alternativos de um produto após fusão ou renomeação, para não quebrar buscas e integrações externas que ainda usam o código antigo.

## Confirmado no código
- Modelo: `produto_identity_models.py:8-21` (`ProdutoSkuAlias`).
- Colunas: `produto_id`, `sku`, `sku_normalizado` (unique por tenant), `origem`, `motivo`, `user_id`.
- Unique `(tenant_id, sku_normalizado)`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id`, `user_id → users.id`.
- Sem referências reversas.

## Utilizado por
- `services/produto_sku_service.py` (`buscar_produtos_por_skus`, `buscar_produto_por_sku`, linhas 84-158).
- `services/produto_alias_service.py`, `services/produto_merge_safety.py`.

## Não identificado
- Nada notável.
