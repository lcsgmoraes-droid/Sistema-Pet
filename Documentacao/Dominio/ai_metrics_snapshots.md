---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_metrics_snapshots

Ver [[ai_decision_logs]].

## Definição
Snapshot agregado de métricas de decisão de IA por período. Parte do módulo órfão `ai_core/` — ver [[ai_decision_logs]].

## Confirmado no código
- Modelo: `ai_core/models/decision_log.py:182-245` (`AIMetricsSnapshotModel`).
- ⚠️ Mesma nomenclatura enganosa de [[ai_review_queue]]: `tenant_id → users.id`.
- `UniqueConstraint(tenant_id, decision_type, period, period_start)`. Períodos: daily/weekly/monthly/all_time.

## Relacionamentos
- FK de saída: `tenant_id → users.id` (⚠️ nome enganoso).

## Utilizado por
- Só internamente ao pacote `ai_core/` — ver achado de módulo órfão em [[ai_decision_logs]].

## Não identificado
- Ver [[ai_decision_logs]].
