---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_feedback_logs

Ver [[ai_decision_logs]].

## Definição
Feedback humano sobre uma decisão de IA (aprovado/rejeitado/corrigido). Parte do módulo órfão `ai_core/` — ver [[ai_decision_logs]].

## Confirmado no código
- Modelo: `ai_core/models/decision_log.py:75-101` (`FeedbackLog`).
- FK `decision_id → ai_decision_logs.id` (unique, 1:1).

## Relacionamentos
- FKs de saída: `decision_id → ai_decision_logs.id`, `user_id → users.id`.

## Utilizado por
- Só internamente ao pacote `ai_core/` — ver achado de módulo órfão em [[ai_decision_logs]].

## Não identificado
- Ver [[ai_decision_logs]].
