---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — lancamentos_manuais

Ver [[contas_bancarias]], [[categorias_financeiras]], [[lancamentos_recorrentes]].

## Definição
Lançamento financeiro manual (entrada ou saída), previsto/realizado/cancelado, com suporte a geração automática assistida por IA.

## Confirmado no código
- Modelo: `financeiro/models_caixa.py:107-168` (`LancamentoManual`).
- Colunas: `tipo` (entrada/saida), `valor`, `status` (previsto/realizado/cancelado), `gerado_automaticamente`, `confianca_ia`.

## Relacionamentos
- FKs de saída: `categoria_id → categorias_financeiras.id`, `conta_bancaria_id → contas_bancarias.id`, `lancamento_recorrente_id → lancamentos_recorrentes.id`, `user_id → users.id`.
- Referenciada por: `ia/aba7_extrato_models.py:143` (`ForeignKey("lancamentos_manuais.id")`).

## Utilizado por
- `contas_receber_criacao_routes.py`, `contas_receber_recorrencias_routes.py`, `estoque/transferencia_parceiro_baixa_lote_service.py`.

## Não identificado
- Nada notável.
