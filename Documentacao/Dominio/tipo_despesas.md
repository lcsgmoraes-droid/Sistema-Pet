---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — tipo_despesas

Ver [[dre_subcategorias]], [[ContaPagar]].

## Definição
Classifica uma despesa como custo fixo ou variável, ligada a uma subcategoria de DRE.

## Confirmado no código
- Modelo: `financeiro/models_catalogos.py:125-147` (`TipoDespesa`).
- Colunas: `e_custo_fixo` (bool, True=Fixo/False=Variável), `ativo`.
- Relationship: `contas = relationship("ContaPagar", back_populates="tipo_despesa")`.

## Relacionamentos
- FK de saída: `dre_subcategoria_id → dre_subcategorias.id` (NOT NULL).
- Referenciada por: [[ContaPagar]].

## Utilizado por
- `caixa_routes.py`, `dashboard/ponto_equilibrio_margem.py`, `dashboard/ponto_equilibrio_routes.py`.

## Não identificado
- Nada notável.
