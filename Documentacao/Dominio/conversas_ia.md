---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conversas_ia

Ver [[mensagens_chat]], [[contexto_financeiro_chat]].

## Definição
Conversa de chat com a IA financeira do CorePet. ⚠️ Reaproveitada fora do escopo original pelo módulo veterinário (acoplamento cross-domain notável).

## Confirmado no código
- Modelo: `ia/aba6_models.py:29-48` (`ConversaIA`).
- ⚠️ `usuario_id` sem FK — comentário no código diz "FK removida temporariamente".
- Relationship 1:N com [[mensagens_chat]] (cascade delete-orphan).

## Relacionamentos
- Sem FK de saída real.
- Referenciada por: [[mensagens_chat]]`.conversa_id`.

## Utilizado por
- `ia/aba6_chat_ia_parts/{conversas,facade,mensagens}.py`.
- ⚠️ Reaproveitada por `veterinario_ia.py`/`veterinario_ia_routes.py` (importam `Conversa, MensagemChat` deste módulo financeiro para o assistente veterinário) — mesma tabela serve dois domínios de negócio distintos.

## Não identificado
- `usuario_id` deveria ser FK real.
