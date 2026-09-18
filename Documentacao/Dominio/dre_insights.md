---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_insights

Ver [[dre_periodos]].

## Definição
Insight gerado por IA sobre um período de DRE (com controle de leitura/aplicação pelo usuário).

## Confirmado no código
- Modelo: `ia/aba7_models.py:187-208` (`DREInsight`).
- Colunas: `foi_lido`, `foi_aplicado`.

## Relacionamentos
- FK de saída: `dre_periodo_id → dre_periodos.id`.

## Utilizado por
- Módulo DRE Inteligente.

## Não identificado
- Nada notável.
