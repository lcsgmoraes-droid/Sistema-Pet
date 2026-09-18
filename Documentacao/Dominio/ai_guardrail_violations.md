---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_guardrail_violations

Ver [[ai_decision_logs]], [[ai_circuit_breaker_logs]].

## Definição
Violação de guardrail de segurança do framework de IA. Parte do módulo órfão `ai_core/` — ver [[ai_decision_logs]].

## Confirmado no código
- Modelo: `ai_core/models/safety_log.py:21-60` (`AIGuardrailViolationLog`).
- `tenant_id` sem FK (Integer indexado — diferente do padrão FK-para-users dos outros modelos do mesmo pacote).
- Colunas: `severity` (warning/critical/emergency), `guardrail_type`, `circuit_breaker_triggered`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- Só internamente ao pacote `ai_core/` (`safety_service.py`) — ver achado de módulo órfão em [[ai_decision_logs]].

## Não identificado
- Ver [[ai_decision_logs]].
