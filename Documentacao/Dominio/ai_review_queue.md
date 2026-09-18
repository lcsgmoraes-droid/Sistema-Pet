---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_review_queue

Ver [[ai_decision_logs]].

## Definição
Fila de revisão humana de decisões de IA. Parte do módulo órfão `ai_core/` — ver [[ai_decision_logs]].

## Confirmado no código
- Modelo: `ai_core/models/decision_log.py:116-163` (`ReviewQueueModel`).
- ⚠️ Nomenclatura enganosa: coluna `tenant_id` tem `ForeignKey("users.id")` — aponta para `users`, não para uma tabela de tenants, apesar do nome.
- `priority`/`status` (fila de revisão).

## Relacionamentos
- FKs de saída: `decision_log_id → ai_decision_logs.id`, `tenant_id → users.id` (⚠️ nome enganoso), `reviewed_by → users.id`.

## Utilizado por
- Só internamente ao pacote `ai_core/` — ver achado de módulo órfão em [[ai_decision_logs]].

## Não identificado
- Nome da coluna `tenant_id` deveria ser renomeado se de fato aponta para `users`, para evitar confusão.
