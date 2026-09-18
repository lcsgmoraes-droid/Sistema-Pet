---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ops_recovery_actions

Ver [[ops_error_events]].

## Definição
Log de ação automática de recuperação/watchdog (ex.: restart de processo).

## Confirmado no código
- Modelo: `ops_models.py:92-115` (`OpsRecoveryAction`). Colunas: `action_key` (unique), `action_type`, `status`, `pid`/`uvicorn_pid`/`hostname`, `started_at`/`finished_at`, `payload` (JSON).

## Relacionamentos
- Sem FK real.

## Utilizado por
- `services/ops_persistence_service.py`, alimentado por `services/watchdog_event_reporter.py`.

## Não identificado
- Nada notável.
