---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — whatsapp_ia_messages

Ver [[whatsapp_ia_sessions]].

## Definição
Mensagem trocada numa sessão de WhatsApp (recebida ou enviada), com metadados de IA.

## Confirmado no código
- Modelo: `whatsapp/models.py:163-216` (`WhatsAppMessage`). `tenant_id → tenants.id` real, `session_id → whatsapp_ia_sessions.id`, `sent_by_user_id → users.id`.
- Índice único parcial em `(tenant_id, whatsapp_message_id)` só quando `whatsapp_message_id` não é nulo/vazio — evita duplicar mensagem idempotentemente por provider ID, mas permite múltiplas linhas com ID nulo (mensagens internas/geradas pelo bot antes de enviar).
- Colunas: `tipo` (recebida/enviada), `conteudo`, `intent_detected`, `model_used`, `tokens_input/output`, `processing_time_ms`, `message_metadata` (renomeado para evitar conflito com atributo reservado do SQLAlchemy).

## Relacionamentos
- FKs de saída: `tenant_id`, `session_id`, `sent_by_user_id`.

## Utilizado por
- Pipeline de IA/processor do WhatsApp (`processor_response_flow.py`, `processor_ai_flow.py`), `routes/whatsapp_routes.py`/`analytics_router.py`.

## Não identificado
- Nada notável.
