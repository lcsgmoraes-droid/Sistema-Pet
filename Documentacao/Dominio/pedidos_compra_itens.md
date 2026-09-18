---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedidos_compra_itens

Ver [[pedidos_compra]], [[Produto]], [[produto_lotes]].

## Definição
Item de linha de um [[pedidos_compra|pedido de compra]], com controle de quantidade pedida vs. recebida.

## Confirmado no código
- Modelo: `produtos_compras_models.py:121-160` (`PedidoCompraItem`).
- Colunas: `quantidade_pedida`, `quantidade_recebida` (default 0), `unidade_compra`, `quantidade_por_embalagem`, `quantidade_total_unidades`, `preco_unitario`, `desconto_item`, `valor_total`, `status` (pendente/recebido_parcial/recebido_total/cancelado), `sugestao_ia`/`motivo_ia`.

## Relacionamentos
- FKs de saída: `pedido_compra_id → pedidos_compra.id`, `produto_id → produtos.id`.
- Sem referências de entrada.

## Utilizado por
- `pedidos_compra/recebimento_routes.py:82-102,125-140` — recebimento incrementa `quantidade_recebida`, recalcula `status`, e **cria [[produto_lotes|ProdutoLote]] e atualiza `produto.estoque_atual` diretamente** — ponto de integração com estoque paralelo ao fluxo via [[notas_entrada]].

## Não identificado
- ⚠️ Ver achado transversal: existem dois caminhos distintos de entrada física em estoque a partir do módulo de compras (via recebimento de pedido, aqui, e via processamento de nota de entrada) — vale unificar ou documentar claramente quando cada um se aplica.
