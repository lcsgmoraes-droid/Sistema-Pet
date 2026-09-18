---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — bling_flow_incidents

Ver [[bling_flow_events]], [[pedidos_integrados]].

## Definição
Incidente detectado no fluxo de sincronização Bling, com sugestão de correção e auto-fix opcional.

## Confirmado no código
- Modelo: `bling_flow_monitor_models.py:36-68` (`BlingFlowIncident`).
- Colunas: `code`, `severity` (default "medium"), `status` (default "open"), `source` (default "auditoria"), `scope` (default "pedido"), `title`/`message`/`suggested_action`, `auto_fixable`/`auto_fix_status` (default "pending"), `dedupe_key` (⚠️ não é único a nível de schema, só tem `Index`, apesar do nome sugerir unicidade), `first_seen_em`/`last_seen_em`/`resolved_em`/`occurrences`.
- Mesmas FKs fantasmas de [[bling_flow_events]]: `pedido_integrado_id`/`pedido_bling_id`/`nf_bling_id`/`sku`.

## Relacionamentos
- Sem FK real de saída nem entrada.

## Utilizado por
- Criado em `services/bling_flow_monitor_incidents.py:192`; corrigido/resolvido via `bling_flow_monitor_routes.py` (reexposto por `bling_routes.py`, ver [[bling_flow_events]]), `services/bling_flow_monitor_autofix.py`/`bling_flow_monitor_auditoria.py`.

## Não identificado
- `dedupe_key` deveria ter `UniqueConstraint` se o nome reflete a intenção real de deduplicação.
