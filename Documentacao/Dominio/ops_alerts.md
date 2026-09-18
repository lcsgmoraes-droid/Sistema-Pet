---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ops_alerts

Ver [[ops_error_events]], [[ops_recovery_actions]].

## Definição
Alerta operacional agregado (deduplicado) a partir de eventos de erro/recuperação da plataforma.

## Confirmado no código
- Modelo: `ops_models.py:53-89` (`OpsAlert`). `tenant_id` nullable, sem FK — mesma assimetria de [[ops_error_events]], notável em contraste com [[ops_tenant_onboarding_notes]] (que tem FK real, mesmo arquivo).
- Colunas: `alert_key` (unique), `scope`, `kind`, `severity`, `status` (default "open"), `occurrence_count`, `score`, `payload` (JSON), `resolved_at`.

## Relacionamentos
- Sem FK real.

## Utilizado por
- `services/ops_persistence_service.py` (upsert por `alert_key`), `services/ops_dashboard_service.py`.

## Não identificado
- Nada além da assimetria de FK já citada.
