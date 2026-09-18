---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_candidato_evidencias

Ver [[catalogo_mestre_produto_candidatos]].

## Definição
Evidência (arquivo privado, nunca publicado) de suporte a um candidato de produto do catálogo mestre.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:250-285` (`CatalogoMestreCandidatoEvidencia`).
- Colunas: `staging_path`, `hash_arquivo`. `UniqueConstraint(candidato_id, hash_arquivo)`.

## Relacionamentos
- FK de saída: `candidato_id → catalogo_mestre_produto_candidatos.id` (CASCADE).

## Utilizado por
- Fluxo de curadoria do catálogo mestre.

## Não identificado
- Ver achados gerais em [[catalogo_mestre_produtos]].
