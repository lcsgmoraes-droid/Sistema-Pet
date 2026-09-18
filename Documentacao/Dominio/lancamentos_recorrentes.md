---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — lancamentos_recorrentes

Ver [[lancamentos_manuais]], [[contas_bancarias]], [[categorias_financeiras]].

## Definição
Template de lançamento recorrente (frequência, dia de vencimento) que gera `lancamentos_manuais` mês a mês.

## Confirmado no código
- Modelo: `financeiro/models_caixa.py:171-228` (`LancamentoRecorrente`).
- Colunas: `frequencia`, `dia_vencimento`, `ativo`, `data_inicio`/`data_fim`, `ultimo_mes_gerado`, `permite_ajuste_ia`.

## Relacionamentos
- FKs de saída: `categoria_id → categorias_financeiras.id` (NOT NULL), `conta_bancaria_id → contas_bancarias.id`, `user_id → users.id`.
- Referenciada por: [[lancamentos_manuais]]`.lancamento_recorrente_id`.

## Utilizado por
- `lancamentos_routes.py`.

## Não identificado
- Nada notável.
