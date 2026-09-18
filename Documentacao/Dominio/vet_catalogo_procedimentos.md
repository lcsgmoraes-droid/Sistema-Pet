---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_catalogo_procedimentos

Ver [[vet_procedimentos_consulta]], [[vet_orcamento_itens]].

## Definição
Catálogo configurável de procedimentos (cirurgia, exame, consulta, tosa etc.), com valor padrão e insumos padrão.

## Confirmado no código
- Modelo: `veterinario_models.py:564-579` (`CatalogoProcedimento`).
- Colunas: `valor_padrao` (DECIMAL), `insumos` (JSON — lista de insumos padrão, provavelmente com `produto_id`).

## Relacionamentos
- Referenciada por: [[vet_procedimentos_consulta]]`.catalogo_id` (nullable), [[vet_orcamento_itens]]`.catalogo_id` (nullable).

## Utilizado por
- `veterinario_catalogo_routes.py` (CRUD).

## Não identificado
- Nada notável.
