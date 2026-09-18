---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Conta a Pagar

Ver [[Financeiro]], [[Cliente]] (fornecedor).

## Confirmado no código
- Modelo: `backend/app/financeiro/models_contas.py` (`ContaPagar`, junto com `Pagamento`).
- `fornecedor_id` → `clientes.id` (reaproveitamento de `Cliente`, ver [[Cliente]]).
- `categoria_id` → `categorias_financeiras.id`, `tipo_despesa_id` → `tipo_despesas.id`.
- `user_id` → `users.id` (quem lançou/aprovou).
- Auto-FK `conta_principal_id` para **parcelamento** (várias parcelas apontam para a conta "principal").
- Auto-FK `conta_recorrencia_origem_id` para contas geradas por recorrência automática.
- Tem muitos `Pagamento` (histórico de baixas parciais/totais).

## Utilizado por
- [[Financeiro]] (contas a pagar, DRE, fluxo de caixa)
- [[Bling]] (fornecedores sincronizados, potencialmente)

## Não identificado
- ❓ Regras exatas de aprovação/alçada para lançamento de conta a pagar (se existir workflow de aprovação, não foi confirmado nesta rodada).
