---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — movimentacoes_caixa

Ver [[caixas]], [[Venda]].

## Definição
Lançamento dentro de uma sessão de [[caixas|caixa]] — venda, suprimento, sangria, despesa, transferência ou devolução.

## Confirmado no código
- Modelo: `caixa_models.py:71-126` (`MovimentacaoCaixa`).
- Colunas: `caixa_id`, `venda_id` (opcional), `tipo` (venda/suprimento/sangria/despesa/transferencia/devolucao), `fornecedor_id`/`fornecedor_nome`, `conta_origem_id`/`conta_destino_id` (⚠️ Integer soltos sem FK), `usuario_id` (⚠️ Integer sem FK).

## Relacionamentos
- FKs de saída: `caixas.id` (CASCADE), `vendas.id` (⚠️ sem `ondelete` definido, diferente do padrão do resto do módulo).
- Sem referências de entrada.

## Utilizado por
- Criação: `caixa_routes.py:335` (endpoint `POST /{caixa_id}/movimentacao`).
- `caixa/service.py`, `vendas/cancelamento_service.py`, `clientes/financeiro_baixa_lote_routes.py`.
- `ia/aba5_fluxo_caixa_parts/*.py` (projeções e índices de fluxo de caixa usados pela IA financeira).

## Não identificado
- ⚠️ Mesmo padrão de "FK fantasma" (`fornecedor_id`, `conta_origem_id`, `conta_destino_id`, `usuario_id`) visto em [[caixas]] e [[venda_pagamentos]].
