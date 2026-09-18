---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — whatsapp_ia_sessions

Ver [[Tenant]], [[Cliente]], [[whatsapp_ia_messages]], [[whatsapp_handoffs]].

## Definição
Sessão de conversa do WhatsApp (bot ou atendimento humano).

## Confirmado no código
- Modelo: `whatsapp/models.py:126-160` (`WhatsAppSession`). `tenant_id → tenants.id` real.
- Colunas: `phone_number`, `status` (bot/human/waiting_human/closed, default "bot"), `context`, `last_intent`, `message_count`, `started_at`/`last_message_at`/`closed_at`.

## Relacionamentos
- FKs de saída: `cliente_id → clientes.id`, `assigned_to → users.id` (atendente humano).
- Referenciada por: [[whatsapp_ia_messages]]`.session_id`, [[whatsapp_handoffs]]`.session_id`, [[whatsapp_internal_notes]]`.session_id`.

## Utilizado por
- `whatsapp/processor.py` e mixins (`processor_*_flow.py`), `context_manager.py` — núcleo do fluxo de atendimento.

## Não identificado
- Nada notável.
