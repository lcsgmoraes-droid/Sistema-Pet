---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — contas_bancarias

Ver [[movimentacoes_financeiras]], [[ContaPagar]], [[ContaReceber]].

## Definição
Conta bancária ou carteira digital do tenant (corrente/poupança/caixa físico/carteira digital), origem/destino de toda movimentação financeira.

## Confirmado no código
- Modelo: `financeiro/models_caixa.py:21-53` (`ContaBancaria`). Note que `financeiro_models.py` (raiz) é só uma fachada de compatibilidade que reexporta este e outros modelos de `financeiro/*` — não define nenhuma classe própria (linhas 8-54).
- Colunas: `nome`, `tipo`, `banco`/`agencia`/`conta`, `saldo_inicial`, `saldo_atual`, `instituicao_bancaria` (flag banco real vs. carteira digital), `ativa`.

## Relacionamentos
- FK de saída: `user_id → users.id`.
- Referenciada por: `movimentacoes_financeiras.conta_bancaria_id`, `lancamentos_manuais.conta_bancaria_id`, `lancamentos_recorrentes.conta_bancaria_id`, `formas_pagamento.conta_bancaria_destino_id`, `extratos_bancarios.conta_bancaria_id`, `movimentacoes_bancarias.conta_bancaria_id`/`.transferencia_destino_conta_id`.
- Relationship `movimentacoes` com `cascade="all, delete-orphan"` — apagar a conta apaga o extrato unificado associado.

## Utilizado por
- `contas_bancarias_routes.py`, `conciliacao_bancaria_routes.py`, `contas_receber_consulta_routes.py`.

## Não identificado
- Nada notável além do cascade agressivo já citado.
