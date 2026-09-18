---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_learning_patterns

Ver [[ai_decision_logs]].

## Definição
Padrão aprendido pelo framework de IA, com taxa de sucesso e expiração. Parte do módulo órfão `ai_core/` — ver [[ai_decision_logs]].

## Confirmado no código
- Modelo: `ai_core/models/decision_log.py:255-281` (`LearningPatternModel`).
- Colunas: `confidence_boost`, `occurrences`, `success_rate`, `expires_at`.

## Relacionamentos
- FK de saída: `user_id → users.id`.

## Utilizado por
- Só internamente ao pacote `ai_core/` — ver achado de módulo órfão em [[ai_decision_logs]].

## Não identificado
- Ver [[ai_decision_logs]].
