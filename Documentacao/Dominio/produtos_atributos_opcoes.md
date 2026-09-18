---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produtos_atributos_opcoes

Ver [[produtos_atributos]], [[produtos_variacoes_atributos]].

## Definição
Valor possível de um atributo de variação (ex.: "15kg", "Carne"), com ajuste de preço opcional.

## Confirmado no código
- Modelo: `produtos_lembretes_variacoes_models.py:290-332` (`ProdutoAtributoOpcao`).
- Colunas: `atributo_id`, `valor`, `ordem`, `ajuste_preco` (Float), `ajuste_preco_tipo` (fixo/percentual), `codigo_extra`, `ativo`.

## Relacionamentos
- FK de saída: `atributo_id → produtos_atributos.id`.
- Referenciada por: [[produtos_variacoes_atributos]].`opcao_id`; back_populates `ProdutoAtributo.opcoes`.

## Utilizado por
- `services/gerador_variacoes_service.py` (linhas 117-122).

## Não identificado
- Nada notável.
