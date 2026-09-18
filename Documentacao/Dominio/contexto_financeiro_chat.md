---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — contexto_financeiro_chat

## Definição
Cache de contexto financeiro por tipo (índices/projeções/alertas/transações), usado para alimentar respostas do chat IA.

## Confirmado no código
- Modelo: `ia/aba6_models.py:79-93` (`ContextoFinanceiroChat`).
- `usuario_id` sem FK. `valido_ate` (expiração de cache).

## Relacionamentos
- Sem FK real.

## Utilizado por
- `ia/aba6_chat_ia_parts/*.py`.

## Não identificado
- Nada notável além da ausência de FK.
