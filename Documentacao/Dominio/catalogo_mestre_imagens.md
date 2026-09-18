---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — catalogo_mestre_imagens

Ver [[catalogo_mestre_produtos]].

## Definição
Imagem de um produto do catálogo mestre, com proveniência e direitos de uso.

## Confirmado no código
- Modelo: `catalogo_mestre_models.py:139-191` (`CatalogoMestreImagem`).
- Colunas: `tipo_origem`, `gerada_por_ia`, `direitos_uso_status`, `status_revisao`. `UniqueConstraint(produto_id, url_origem)`.

## Relacionamentos
- FK de saída: `produto_id → catalogo_mestre_produtos.id` (CASCADE).

## Utilizado por
- `catalogo_mestre_image_import.py`.

## Não identificado
- Ver achados gerais em [[catalogo_mestre_produtos]] (ausência de rota HTTP, scheduler nunca instanciado).
