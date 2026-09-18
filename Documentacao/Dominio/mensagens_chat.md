---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — mensagens_chat

Ver [[conversas_ia]].

## Definição
Mensagem de uma [[conversas_ia|conversa de chat IA]] (financeiro ou, por reaproveitamento, veterinário).

## Confirmado no código
- Modelo: `ia/aba6_models.py:54-73` (`MensagemChat`).

## Relacionamentos
- FK de saída: `conversa_id → conversas_ia.id` (correta).

## Utilizado por
- `ia/aba6_chat_ia_parts/*.py`, `veterinario_ia.py`/`veterinario_ia_routes.py` (reaproveitamento cross-domain).

## Não identificado
- Nada notável.
