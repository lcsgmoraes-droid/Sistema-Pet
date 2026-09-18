---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conversas_whatsapp

Ver [[Usuario]], [[Cliente]], [[Venda]], [[mensagens_whatsapp]].

## Definição
Conversa de WhatsApp comercial (assistente de vendas), com estado e resultado de venda associado. Não confundir com [[whatsapp_ia_sessions]] (módulo de atendimento/handoff mais novo, `whatsapp/models.py`) — este é um módulo mais antigo (`ia/aba6_aba9_models.py`).

## Confirmado no código
- Modelo: `ia/aba6_aba9_models.py:31-71` (`ConversaWhatsApp`).
- Colunas: `estado_atual`, `resultado_venda`, `rating_cliente`.
- ⚠️ **FKs fantasmas com nome de tabela errado**: `usuario_id` tem `ForeignKey("usuarios.id")` e `cliente_id` tem `ForeignKey("cliente.id")` — mas as tabelas reais são `users` e `clientes` (plural), não `usuarios`/`cliente`. Essas FKs nunca resolvem de verdade.
- `venda_id → vendas.id` está correta.

## Relacionamentos
- FKs de saída: `usuario_id` (⚠️ aponta para tabela inexistente "usuarios"), `cliente_id` (⚠️ aponta para tabela inexistente "cliente"), `venda_id → vendas.id` (correta).
- Referenciada por: [[mensagens_whatsapp]]`.conversa_id`.

## Utilizado por
- `routes/whatsapp_routes.py`.

## Não identificado
- 🔴 As duas FKs fantasmas com nome de tabela errado deveriam ser corrigidas para `users.id`/`clientes.id`.
