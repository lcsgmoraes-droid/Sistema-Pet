---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — whatsapp_agents

Ver [[Tenant]], [[Usuario]], [[whatsapp_handoffs]].

## Definição
Papel de atendente humano de WhatsApp, vinculado a um usuário do sistema.

## Confirmado no código
- Modelo: `whatsapp/models_handoff.py:25-53` (`WhatsAppAgent`). `tenant_id → tenants.id`, `user_id → users.id`.
- Colunas: `name`, `email`, `status` (online/offline/busy/away, default "offline"), `max_concurrent_chats`/`current_chats`, `auto_assign`, `receive_notifications`.
- ⚠️ Relationship unilateral: `tenant = relationship("Tenant")` com comentário `# TODO: Descomentar quando relationship no Tenant estiver configurado` — sem back_populates no lado do Tenant.

## Relacionamentos
- FKs de saída: `tenant_id`, `user_id`.
- Referenciada por: [[whatsapp_handoffs]]`.assigned_to`, [[whatsapp_internal_notes]]`.agent_id`.

## Utilizado por
- `whatsapp/handoff_manager.py`, `routers/whatsapp_handoff.py`.

## Não identificado
- Relationship com Tenant incompleto (TODO explícito no código).
