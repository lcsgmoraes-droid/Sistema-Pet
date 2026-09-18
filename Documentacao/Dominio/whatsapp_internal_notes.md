---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — whatsapp_internal_notes

Ver [[whatsapp_handoffs]], [[whatsapp_ia_sessions]], [[whatsapp_agents]].

## Definição
Anotação interna do atendente durante um handoff (não visível ao cliente).

## Confirmado no código
- Modelo: `whatsapp/models_handoff.py:129-165` (`WhatsAppInternalNote`). `tenant_id → tenants.id`, `handoff_id → whatsapp_handoffs.id`, `session_id → whatsapp_ia_sessions.id`, `agent_id → whatsapp_agents.id`.
- Colunas: `note` (Text), `note_type` (general/important/follow_up/warning, default "general").
- ⚠️ Duas properties de compatibilidade: `author_id` (espelha `agent_id`) e `content` (espelha `note`) — nomes alternativos, provavelmente de uma versão anterior do schema.

## Relacionamentos
- FKs de saída: `tenant_id`, `handoff_id`, `session_id`, `agent_id`.

## Utilizado por
- `routers/whatsapp_handoff.py`.

## Não identificado
- ❓ Não confirmado se algum consumidor ainda usa `author_id`/`content` diretamente ou se são vestigiais.
