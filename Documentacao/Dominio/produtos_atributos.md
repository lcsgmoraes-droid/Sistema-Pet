---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produtos_atributos

Ver [[Produto]], [[produtos_atributos_opcoes]], [[produtos_variacoes_atributos]].

## Definição
Atributo de variação de um produto "pai" (ex.: Peso, Sabor, Cor) — base do gerador automático de variações.

## Confirmado no código
- Modelo: `produtos_lembretes_variacoes_models.py:239-287` (`ProdutoAtributo`).
- Colunas: `produto_pai_id` (deve ser produto tipo PAI — regra só validada em service, não em DB), `nome`, `ordem`, `obrigatorio`, `user_id`, `ativo`.

## Relacionamentos
- FKs de saída: `produto_pai_id → produtos.id`, `user_id → users.id`.
- Referenciada por: [[produtos_atributos_opcoes]].`atributo_id`, [[produtos_variacoes_atributos]].`atributo_id`; backref `Produto.atributos`.

## Utilizado por
- `services/gerador_variacoes_service.py` (`generate_variacoes`, linhas 96-101).

## Não identificado
- Nada notável.
