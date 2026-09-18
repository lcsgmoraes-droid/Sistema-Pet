---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_orcamento_itens

Ver [[vet_orcamentos]], [[vet_catalogo_procedimentos]], [[Produto]], [[vet_procedimentos_consulta]].

## Definição
Item de linha de um [[vet_orcamentos|orçamento]] veterinário.

## Confirmado no código
- Modelo: `veterinario_models.py:769-805` (`OrcamentoVetItem`).
- Colunas: `origem` (manual/…), custo/preço unitário e total, margem.
- `relationship("Produto", foreign_keys=[produto_id])` — liga de fato ao módulo de produtos/estoque.

## Relacionamentos
- FKs de saída: `orcamento_id → vet_orcamentos.id`, `catalogo_id → vet_catalogo_procedimentos.id` (nullable), `produto_id → produtos.id` (nullable) — **FK real e direta**, diferente de [[vet_procedimentos_consulta]]`.insumos`, que só guarda `produto_id` dentro de JSON solto.

## Utilizado por
- `veterinario_orcamentos_routes.py`.

## Não identificado
- Ver inconsistência de modelagem já documentada em [[vet_procedimentos_consulta]]: esta tabela usa FK real para produto, a outra usa JSON — duas tabelas semanticamente parecidas com padrões diferentes.
