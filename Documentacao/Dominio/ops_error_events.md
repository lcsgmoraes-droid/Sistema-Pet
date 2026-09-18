---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ops_error_events

Ver [[ops_alerts]], [[Tenant]].

## Definição
Evento de erro de requisição HTTP, para observabilidade de plataforma — tabela global/cross-tenant deliberada.

## Confirmado no código
- Modelo: `ops_models.py:23-50` (`OpsErrorEvent`). `tenant_id` UUID nullable, sem FK — deliberadamente fora do filtro global de tenant (uso administrativo).
- Colunas: `event_key` (unique, dedupe), `user_email`, `request_id`, `method`, `path`, `status_code`, `duration_ms`, `exception_type`/`exception_message`, `client_ip`, `user_agent`, `payload` (JSON).

## Relacionamentos
- Sem FK real.

## Utilizado por
- `services/ops_persistence_service.py` (insert dedupado por `event_key`), `services/error_event_reporter.py`, `routes/error_events_routes.py` (registrado em `main_routers.py:178`).

## Não identificado
- ⚠️ Contém dados sensíveis (`exception_message`, `path`, `user_email`) — tratar com cuidado ao expor via API administrativa.
