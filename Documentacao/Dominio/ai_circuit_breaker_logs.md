---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_circuit_breaker_logs

Ver [[ai_guardrail_violations]].

## Definição
Log de acionamento do circuit breaker do framework de IA (proteção contra decisões automatizadas descontroladas). Parte do módulo órfão `ai_core/` — ver [[ai_decision_logs]].

## Confirmado no código
- Modelo: `ai_core/models/safety_log.py:70-95` (`AICircuitBreakerLog`).
- `tenant_id` sem FK (mesmo padrão de [[ai_guardrail_violations]]).
- Colunas: `state` (open/half_open/closed), `previous_min_confidence`/`new_min_confidence`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- Só internamente ao pacote `ai_core/` (`circuit_breaker.py`) — ver achado de módulo órfão em [[ai_decision_logs]].

## Não identificado
- Ver [[ai_decision_logs]].
