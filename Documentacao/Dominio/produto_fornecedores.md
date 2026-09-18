---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_fornecedores

Ver [[Produto]], [[Cliente]].

## Definição
Vínculo produto ↔ fornecedor, com preço de custo e prazo de entrega. Confirma que não existe cadastro de "fornecedor" dedicado — fornecedores são [[Cliente]] reaproveitado.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:292-315` (`ProdutoFornecedor`).
- Colunas: `produto_id`, `fornecedor_id` (**aponta para `clientes.id`**), `codigo_fornecedor`, `preco_custo`, `prazo_entrega` (dias), `estoque_fornecedor`, `e_principal`, `ativo`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id` (CASCADE), `fornecedor_id → clientes.id`.
- Referenciada por: `Produto.fornecedores_alternativos` (back_populates, cascade delete-orphan) — `produtos_catalogo_models.py:384-386`.

## Utilizado por
- `services/bling_cost_sync_service.py` (`selecionar_produto_fornecedor_bling`), `services/pessoa_merge_service.py`, `services/produto_merge_service.py`.

## Não identificado
- ❓ Onde exatamente o `Cliente` é marcado como "é fornecedor" (flag/tipo) não foi confirmado nesta pesquisa — ver [[Cliente]].
