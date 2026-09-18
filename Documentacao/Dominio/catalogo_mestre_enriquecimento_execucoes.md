---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_enriquecimento_execucoes

Ver [[catalogo_mestre_pendencias]], [[catalogo_mestre_produtos]].

## Definição
Auditoria de cada execução de enriquecimento por IA de um produto do catálogo mestre.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:347-383` (`CatalogoMestreEnriquecimentoExecucao`).
- Colunas: `provedor`, `modelo`, `versao_prompt`, `worker_id`.

## Relacionamentos
- FKs de saída: `pendencia_id → catalogo_mestre_pendencias.id` (SET NULL), `produto_id → catalogo_mestre_produtos.id` (SET NULL).

## Utilizado por
- `catalogo_mestre_enrichment_worker.py`.

## Não identificado
- Ver achados gerais em [[catalogo_mestre_produtos]].
