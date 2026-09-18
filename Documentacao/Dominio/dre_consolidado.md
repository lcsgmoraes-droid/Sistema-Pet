---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — dre_consolidado

Ver [[dre_detalhe_canais]].

## Definição
Soma de todos os canais do DRE detalhado.

## Confirmado no código
- Modelo: `ia/aba7_dre_detalhada_models.py:100-158` (`DREConsolidado`).
- ⚠️ `receita_por_canal`/`despesas_por_canal` são JSON serializado em `Text`, não coluna `JSON` nativa — mesmo padrão de inconsistência já visto em [[estoque_movimentacoes]].

## Relacionamentos
- Sem FK real.

## Utilizado por
- `domain/dre/fechamento_engine.py`, `domain/ia/dre_context_provider.py`.

## Não identificado
- Mesma lacuna de registro no Alembic de [[dre_detalhe_canais]].
