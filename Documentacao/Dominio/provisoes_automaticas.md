---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — provisoes_automaticas

Ver [[regras_conciliacao]], [[ContaPagar]], [[movimentacoes_bancarias]].

## Definição
Provisão financeira gerada automaticamente para contas recorrentes (conceito descrito no código, mas ⚠️ sem evidência de uso real).

## Confirmado no código
- Modelo: `financeiro/models_conciliacao.py:148-172` (`ProvisaoAutomatica`).
- Colunas: liga uma regra de conciliação a uma conta a pagar e à movimentação bancária real que a "resolveu".

## Relacionamentos
- FKs de saída: `regra_id → regras_conciliacao.id`, `conta_pagar_id → contas_pagar.id`, `movimentacao_real_id → movimentacoes_bancarias.id` (SET NULL).
- Sem referências de entrada.

## Utilizado por
- ⚠️ **Nenhum uso confirmado fora da própria definição e do facade `financeiro_models.py`.** Nenhuma rota/service instancia ou consulta esta tabela.

## Não identificado
- 🟡 Modelo aparentemente morto/nunca implementado no fluxo real, apesar de descrito como feature no código. Candidato a confirmar com o time se é roadmap futuro ou resquício abandonado.
