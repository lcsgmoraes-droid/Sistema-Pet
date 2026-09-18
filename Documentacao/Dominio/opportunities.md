---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — opportunities

Ver [[opportunity_events]], [[Cliente]], [[Produto]].

## Definição
🔴 **Tabela órfã confirmada.** Oportunidade de cross-sell/up-sell/recorrência do PDV — modelo pronto, mas nunca ligado a nenhum fluxo real.

## Confirmado no código
- Modelo: `opportunities_models.py:30-105` (`Opportunity`).
- Colunas: `cliente_id` (UUID, sem FK), `contexto` (default "PDV"), `tipo` (cross_sell/up_sell/recorrencia), `produto_origem_id`/`produto_sugerido_id` (UUID, sem FK — comentário do módulo diz explicitamente "NÃO integra com IA... apenas estrutura para... aprendizado futuro"), `extra_data` (JSONB).

## Relacionamentos
- Sem FK de saída real.
- [[opportunity_events]]`.opportunity_id` é referência lógica, não FK real.

## Utilizado por
- 🔴 **Nenhum uso confirmado.** `grep` fora do próprio arquivo só retorna registro de metadata (`db/base.py`) e whitelist de tabelas tenant-safe. Nenhum `insert`/query real em produção.

## Não identificado
- Confirma que é scaffolding para fase futura não implementada — diferente de [[opportunity_events]] (irmã desta tabela), que está em uso ativo.
