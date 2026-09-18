---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Conta a Receber

Ver [[Financeiro]], [[Venda]].

## Confirmado no código
- Modelo: `backend/app/financeiro/models_contas.py` (`ContaReceber`, junto com `Recebimento`).
- Gerada a partir de uma [[Venda]] a prazo (relação `viewonly` `Venda.contas_receber`).
- Estrutura de parcelamento/recorrência análoga à de [[ContaPagar]] (mesmo padrão de modelagem).
- Conciliação bancária relacionada em `financeiro/models_conciliacao.py` (`ExtratoBancario`, `MovimentacaoBancaria`, `ProvisaoAutomatica`).

## Utilizado por
- [[Financeiro]] (contas a receber, DRE, fluxo de caixa, conciliação)
- [[PDV-Vendas]] (origem da conta, quando a venda é a prazo)

## Não identificado
- ❓ Regra de inadimplência/negativação (se existe fluxo automatizado, não confirmado nesta rodada).
