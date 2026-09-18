---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — stone_transaction_logs

Ver [[stone_transactions]].

## Definição
⚠️ Código morto, parte do mesmo módulo órfão de [[stone_transactions]].

## Confirmado no código
- Modelo: `stone_models.py:152-209` (`StoneTransactionLog`).
- FKs: `transaction_id → stone_transactions.id`, `user_id → users.id` (nullable).

## Relacionamentos
- Única referência de entrada real é dentro do próprio arquivo órfão (`relationship("StoneTransaction", back_populates="logs")`).

## Utilizado por
- Nada — código morto.

## Não identificado
- Ver [[stone_transactions]] para o achado completo.
