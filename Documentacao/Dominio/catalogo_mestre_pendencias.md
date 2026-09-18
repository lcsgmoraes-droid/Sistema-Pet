---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_pendencias

Ver [[catalogo_mestre_produtos]], [[catalogo_mestre_enriquecimento_execucoes]].

## Definição
Fila de enriquecimento de produto do catálogo mestre, com reserva e retry.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:291-341` (`CatalogoMestrePendencia`).
- Colunas: `reservada_por`, `reserva_expira_em`, `tentativas`, `proxima_tentativa_em`. `UniqueConstraint(produto_id, tipo, posicao_alvo)`.

## Relacionamentos
- FK de saída: `produto_id → catalogo_mestre_produtos.id` (CASCADE).
- Referenciada por: [[catalogo_mestre_enriquecimento_execucoes]]`.pendencia_id`.

## Utilizado por
- `catalogo_mestre_enrichment_worker.py` (`_claim_next`, `_finish_success`, `_clear_reservation`).

## Não identificado
- ⚠️ Fila existe e está bem implementada, mas o worker que a consome só roda manualmente — ver achado do scheduler nunca instanciado em [[catalogo_mestre_produtos]].
