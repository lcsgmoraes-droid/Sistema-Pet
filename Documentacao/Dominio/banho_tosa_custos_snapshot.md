---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — banho_tosa_custos_snapshot

Ver [[banho_tosa_atendimentos]].

## Definição
Breakdown completo de custo (insumos, água, energia, mão de obra, comissão, taxi dog, taxas de pagamento, rateio) e margem calculada por atendimento — usado em relatórios de rentabilidade.

## Confirmado no código
- Modelo: `banho_tosa_model_parts/custos.py:20-49` (`BanhoTosaCustoSnapshot`).
- FK: `atendimento_id → banho_tosa_atendimentos.id` (CASCADE, unique por atendimento).

## Relacionamentos
- ⚠️ O vínculo real é feito pelo lado inverso (`atendimento_id` aqui). O campo `banho_tosa_atendimentos.custo_snapshot_id` é FK fantasma (Integer sem `ForeignKey()`) — redundante/não confiável como referência, já que a relação de verdade é esta tabela apontando para o atendimento, não o contrário.

## Utilizado por
- Relatórios de rentabilidade do módulo.

## Não identificado
- Ver achado de FK fantasma em [[banho_tosa_atendimentos]]`.custo_snapshot_id`.
