---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_categorias

Ver [[dre_subcategorias]].

## Definição
Categoria macro do DRE (Demonstrativo de Resultado): Receita, Custo, Despesa ou Resultado.

## Confirmado no código
- Modelo: `dre_plano_contas_models.py:42-61` (`DRECategoria`).
- Colunas: `ordem`, `natureza` (Enum `NaturezaDRE`: RECEITA/CUSTO/DESPESA/RESULTADO), `ativo`.
- Sem FK de saída.

## Relacionamentos
- Referenciada por: [[dre_subcategorias]]`.categoria_id`.
- Relationship `subcategorias` com `cascade="all, delete-orphan"`.

## Utilizado por
- `dre_plano_contas_routes.py`, `estoque/transferencia_parceiro_support.py`, `estoque_saida_full/financeiro.py`, `scripts/seed_dre_plano_contas_petshop.py`.

## Não identificado
- Nada notável.
