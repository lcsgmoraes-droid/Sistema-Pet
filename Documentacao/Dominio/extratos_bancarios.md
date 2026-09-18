---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — extratos_bancarios

Ver [[contas_bancarias]], [[movimentacoes_bancarias]].

## Definição
Arquivo de extrato bancário (OFX) importado, com contagem de movimentações conciliadas/pendentes.

## Confirmado no código
- Modelo: `financeiro/models_conciliacao.py:24-45` (`ExtratoBancario`).
- Colunas: `arquivo_nome`, `periodo_inicio`/`fim`, `total_movimentacoes`, `conciliadas`, `pendentes`, `status` (processando/concluido/revisao).

## Relacionamentos
- FK de saída: `conta_bancaria_id → contas_bancarias.id` (CASCADE).
- Referenciada por: [[movimentacoes_bancarias]]`.extrato_id`.

## Utilizado por
- `conciliacao_bancaria_routes.py`.

## Não identificado
- Nada notável.
