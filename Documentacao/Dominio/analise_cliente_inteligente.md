---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — analise_cliente_inteligente

Ver [[Cliente]], [[Produto]].

## Definição
Cache de perfil de compra/score de fidelidade de um cliente.

## Confirmado no código
- Modelo: `ia/aba6_aba9_models.py:121-157` (`AnaliseClienteInteligente`).
- ⚠️ Mesmas FKs fantasmas com nome de tabela errado de [[conversas_whatsapp]]: `usuario_id → "usuarios.id"` e `cliente_id → "cliente.id"` (tabelas reais são `users`/`clientes`).
- `produto_favorito_id → produtos.id` está correta.

## Relacionamentos
- FKs de saída: `usuario_id`/`cliente_id` (⚠️ ambas fantasmas com nome errado), `produto_favorito_id → produtos.id` (correta).

## Utilizado por
- ❓ Nenhum uso confirmado fora da própria definição do modelo — possivelmente órfã.

## Não identificado
- ❓ Uso real não confirmado.
- 🔴 Mesmas FKs fantasmas de nome errado de [[conversas_whatsapp]].
