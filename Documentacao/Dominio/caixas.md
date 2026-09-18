---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — caixas

Ver [[Venda]], [[movimentacoes_caixa]].

## Definição
Sessão de caixa do PDV (abertura → operação → fechamento), com valores de abertura/esperado/informado/diferença.

## Confirmado no código
- Modelo: `caixa_models.py:14-68` (`Caixa`).
- Colunas: `usuario_id`/`usuario_fechamento_id` (⚠️ Integer sem FK, apesar do nome sugerir `users`), `valor_abertura`/`valor_esperado`/`valor_informado`/`diferenca` (⚠️ `Float`, não `DECIMAL` — inconsistente com o padrão `DECIMAL(10,2)` usado em `vendas_models.py`), `status` (string livre: aberto/fechado), `conta_origem_id`/`conta_origem_nome` (Integer/String soltos, sem FK), `conferencia_abertura` (JSON).

## Relacionamentos
- Sem FK de saída real declarada na classe (todas as relações "de nome" são Integer solto).
- Referências de entrada: `vendas.caixa_id → caixas.id` (nullable), [[movimentacoes_caixa]]`.caixa_id → caixas.id` (CASCADE).

## Utilizado por
- `caixa_routes.py` — `POST /abrir`, `POST /{id}/fechar`, `POST /{id}/reabrir`, `POST /{id}/movimentacao`, resumo, vendas do caixa.
- `caixa/service.py`, `vendas/cancelamento_service.py`, `vendas/devolucoes_routes.py`.

## Não identificado
- ⚠️ `usuario_id`/`usuario_fechamento_id`/`conta_origem_id` sem FK real apesar do nome — mesmo padrão de "FK fantasma" encontrado em [[venda_pagamentos]].
- Uso de `Float` para valores monetários, potencial fonte de erro de arredondamento — vale revisar com o time.
