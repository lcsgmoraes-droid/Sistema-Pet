---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — historico_classificacao_dre

Ver [[regras_classificacao_dre]], [[dre_subcategorias]], [[ContaPagar]], [[ContaReceber]].

## Definição
Log de auditoria de cada classificação DRE aplicada (manual ou automática), usado para auditoria e retraining do motor de regras.

## Confirmado no código
- Modelo: `dre_regras_models.py:135-193` (`HistoricoClassificacao`).
- Campo `lancamento_id` (Integer, NOT NULL) — referência polimórfica intencional para `contas_pagar` OU `contas_receber`, definida pelo campo `tipo_lancamento` ('pagar'/'receber'), sem `ForeignKey()` real (mesmo padrão de `movimentacoes_financeiras.origem_id`).
- ⚠️ FK fantasma adicional: `classificado_por_user_id` sem `ForeignKey("users.id")`.
- ⚠️ Notável: `valor` é `Integer` com comentário "Valor em centavos" — diferente do padrão `Numeric` usado no resto do módulo financeiro.

## Relacionamentos
- FKs de saída reais: `dre_subcategoria_id → dre_subcategorias.id`, `regra_aplicada_id → regras_classificacao_dre.id` (nullable).
- `lancamento_id` referencia informalmente `contas_pagar`/`contas_receber` conforme `tipo_lancamento`.

## Utilizado por
- `dre_classificacao_service.py`.

## Não identificado
- 🟡 Uso de `Integer` (centavos) para valor monetário é inconsistente com o `Numeric` usado no resto do financeiro — vale padronizar.
