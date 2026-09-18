---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ops_journey_events

Ver [[ops_error_events]].

## Definição
Evento terminal sanitizado por jornada de negócio (ex.: checkout, pagamento) — usado para calcular SLOs.

## Confirmado no código
- Modelo: `ops_models.py:118-150` (`OpsJourneyEvent`). Colunas: `event_key` (unique), `journey`, `outcome`, `reason_code`, `duration_ms`, `status_code`, `provider`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `services/journey_event_reporter.py` (escrita), `services/ops_dashboard_service.py` (leitura/SLO).

## Não identificado
- Nada notável.
