---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — whatsapp_handoffs

Ver [[whatsapp_ia_sessions]], [[whatsapp_agents]].

## Definição
Transferência de uma conversa do bot para atendimento humano, com análise de sentimento e SLA.

## Confirmado no código
- Modelo: `whatsapp/models_handoff.py:56-126` (`WhatsAppHandoff`). `tenant_id → tenants.id`, `session_id → whatsapp_ia_sessions.id`, `assigned_to → whatsapp_agents.id`.
- Colunas: `reason` (auto_sentiment/manual_request/auto_repeat/auto_timeout/auto_complex), `sentiment_score`/`sentiment_label`, `priority` (low/medium/high/urgent), `status` (pending/assigned/in_progress/resolved/cancelled), `resolved_at`/`resolution_notes`/`resolution_time_seconds`, `rating`(1-5)/`rating_feedback`.
- ⚠️ `assigned_agent_id` é uma `@property` que só espelha a coluna real `assigned_to` — não existe como coluna própria no banco.

## Relacionamentos
- FKs de saída: `tenant_id`, `session_id`, `assigned_to`.
- Referenciada por: [[whatsapp_internal_notes]]`.handoff_id`.

## Utilizado por
- `whatsapp/handoff_manager.py`, `routers/whatsapp_handoff.py`, `whatsapp/sentiment.py` (calcula sentimento).

## Não identificado
- `assigned_agent_id` como property pode confundir quem espera encontrar a coluna diretamente no banco.
