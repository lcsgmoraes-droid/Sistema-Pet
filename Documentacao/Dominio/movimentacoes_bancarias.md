---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — movimentacoes_bancarias

Ver [[extratos_bancarios]], [[contas_bancarias]], [[ContaPagar]], [[ContaReceber]], [[regras_conciliacao]], [[dre_subcategorias]].

## Definição
Núcleo da conciliação bancária genérica: cada linha do OFX importado, com status de conciliação e sugestão automática por regra aprendida.

## Confirmado no código
- Modelo: `financeiro/models_conciliacao.py:48-109` (`MovimentacaoBancaria`).
- Colunas: dados OFX (`fitid`, `memo`, `tipo` CREDIT/DEBIT), `status_conciliacao` (pendente/sugerido/conciliado/manual), `confianca_sugestao`, `tipo_vinculo`, `recorrente`/`grupo_recorrencia`.
- Campo `centro_custo_id` (Integer) sem FK, comentado `# Futuro` — placeholder intencional, não erro.

## Relacionamentos
- FKs de saída: `extrato_id → extratos_bancarios.id` (CASCADE), `conta_bancaria_id → contas_bancarias.id` (CASCADE), `fornecedor_id → clientes.id`, `conta_pagar_id → contas_pagar.id` (SET NULL), `conta_receber_id → contas_receber.id` (SET NULL), `transferencia_destino_conta_id → contas_bancarias.id`, `categoria_dre_id → dre_subcategorias.id`, `classificado_por → users.id`, `regra_aplicada_id → regras_conciliacao.id`.
- Referenciada por: `conciliacao_lotes.movimentacao_bancaria_id` (`conciliacao_models.py`), `provisoes_automaticas.movimentacao_real_id`.

## Utilizado por
- `conciliacao_bancaria_routes.py`.

## Não identificado
- `centro_custo_id` é placeholder para feature futura de centro de custo, ainda não implementada.
