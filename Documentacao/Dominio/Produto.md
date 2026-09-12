---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Produto

Ver [[Produtos-Estoque]], [[Venda]], [[Bling]].

## Confirmado no código
- Modelo principal: `backend/app/produtos_catalogo_models.py` (`Produto`), com `produtos_models.py` como facade de compatibilidade que reagrupa modelos espalhados em `produtos_compras_models.py`, `produtos_estoque_models.py`, `estoque_models.py` e outros.
- `categoria_id` → `categorias.id`, `marca_id` → `marcas.id`, `departamento_id` → `departamentos.id`.
- `fornecedor_id` → `clientes.id` (reaproveitamento de `Cliente`, ver [[Cliente]]).
- `produto_pai_id` → auto-FK (`produtos.id`) para variações/kits.
- Relaciona-se com `ProdutoLote` (controle de lote/validade), `ProdutoImagem`, `EstoqueMovimentacao`, `ListaPreco`.
- Faz parte também de um **Catálogo Mestre global** (`catalogo_mestre_models.py`), com worker dedicado de enriquecimento contínuo (`backend/scripts/run_catalogo_mestre_worker.py`) — um conceito de catálogo compartilhado entre tenants, além do catálogo próprio de cada empresa.
- Recorrência de compra (protocolos de recompra) é tratada em `services/product_recurrence.py` e modelos de lembrete associados.

## Utilizado por
- [[Produtos-Estoque]] (cadastro, estoque, movimentações)
- [[PDV-Vendas]] (item vendido)
- [[Bling]] (sincronização de catálogo/estoque)
- [[Fiscal-IntNFe-SEFAZ]] (nota de entrada)
- [[iFood]], E-commerce (catálogo publicado)

## Não identificado
- ❓ Relação de governança entre o Catálogo Mestre global e o catálogo próprio de cada tenant (quem pode editar o quê, e como conflitos são resolvidos) — não auditado a fundo nesta rodada.
