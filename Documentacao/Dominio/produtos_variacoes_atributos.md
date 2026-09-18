---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produtos_variacoes_atributos

Ver [[produtos_atributos]], [[produtos_atributos_opcoes]], [[Produto]].

## Definição
Liga uma variação de produto (`Produto` com `tipo_produto='VARIACAO'`) à opção escolhida para cada atributo — ex.: variação "Ração X 15kg Carne" = atributo Peso→opção 15kg + atributo Sabor→opção Carne.

## Confirmado no código
- Modelo: `produtos_lembretes_variacoes_models.py:335-383` (`ProdutoVariacaoAtributo`).
- Colunas: `variacao_id` (aponta para `produtos.id`), `atributo_id`, `opcao_id`.
- Index unique `(variacao_id, atributo_id)` — uma variação só pode ter uma opção por atributo.

## Relacionamentos
- FKs de saída: `variacao_id → produtos.id`, `atributo_id → produtos_atributos.id`, `opcao_id → produtos_atributos_opcoes.id`.
- Sem referências reversas; backref `Produto.atributos_variacao` (via `variacao_id`).

## Utilizado por
- `services/gerador_variacoes_service.py` (geração automática de combinações de variação).
- `services/variacao_lixeira_service.py` (soft-delete/lixeira de variações — não aprofundado).

## Não identificado
- ❓ Mecânica de `variacao_lixeira_service.py` não aprofundada nesta pesquisa.
