---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_kit_componentes

Ver [[Produto]], [[kit_composicao]].

## Definição
Composição ativa de um kit: liga um produto "kit" aos produtos que o compõem, com quantidade. É a tabela **efetivamente usada** pela lógica de kits do sistema (ver [[kit_composicao]] para uma tabela paralela que existe no banco mas não é usada por nenhum código vivo).

## Confirmado no código
- Modelo: `produtos_estoque_models.py:50-117` (`ProdutoKitComponente`).
- Colunas: `kit_id`, `produto_componente_id`, `quantidade` (Float), `opcional`, `ordem`.
- Unique composto `(kit_id, produto_componente_id)` — linha 86.
- ⚠️ Regras de negócio (kit não pode ter tipo PAI/KIT como componente; `quantidade > 0`) não têm CHECK constraint no banco — dependem inteiramente da service layer validar.

## Relacionamentos
- FKs de saída: `kit_id → produtos.id` (CASCADE), `produto_componente_id → produtos.id` — linhas 95, 100.
- Referenciada por: `Produto.componentes_kit` (via `kit` relationship, linha 116).

## Utilizado por
- `services/kit_custo_service.py`, `services/kit_estoque_service.py` (queries por `kit_id`/`produto_componente_id`), `services/kit_preco_venda_service.py`, `services/produto_merge_service.py`, `services/bling_nf/estoque.py`.

## Não identificado
- Nada notável além da ausência de CHECK constraints já citada.
