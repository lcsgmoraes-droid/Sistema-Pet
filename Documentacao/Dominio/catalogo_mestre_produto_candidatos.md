---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_produto_candidatos

Ver [[catalogo_mestre_produtos]], [[catalogo_mestre_candidato_evidencias]].

## Definição
Candidato a produto do catálogo mestre, em fluxo de curadoria antes de virar produto confirmado.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:197-244` (`CatalogoMestreProdutoCandidato`).
- `UniqueConstraint(gtin)`, `CheckConstraint` de `decisao_escopo_sugerida`.

## Relacionamentos
- FK de saída: `produto_mestre_id → catalogo_mestre_produtos.id` (SET NULL).
- Referenciada por: [[catalogo_mestre_candidato_evidencias]]`.candidato_id`.

## Utilizado por
- Fluxo de curadoria (`catalogo_mestre_service.py`).

## Não identificado
- Ver achados gerais em [[catalogo_mestre_produtos]].
