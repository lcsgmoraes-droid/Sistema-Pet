---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — opportunity_events

Ver [[opportunities]], [[Usuario]].

## Definição
Log de eventos de clique do operador em sugestões do PDV (convertida/refinada/rejeitada) — usado para dashboards de métricas.

## Confirmado no código
- Modelo: `opportunity_events_models.py:32-109` (`OpportunityEvent`).
- Colunas: `opportunity_id` (UUID, referência lógica, não FK real), `event_type` (CONVERTIDA/REFINADA/REJEITADA), `user_id` (UUID, sem FK), `contexto` (default "PDV"), `extra_data` (JSONB).

## Relacionamentos
- Sem FK real de saída (`opportunity_id` e `user_id` são referências soltas).

## Utilizado por
- `api/pdv_internal_routes.py` (persiste evento a partir de clique do operador no PDV).
- `services/opportunity_event_service.py` (`register_event`), `services/opportunity_metrics_service.py` (agregações para dashboards).

## Não identificado
- Ao contrário de [[opportunities]] (órfã), esta tabela está em uso ativo real.
