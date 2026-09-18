---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedidos_compra_notas_entrada

Ver [[pedidos_compra]], [[notas_entrada]].

## Definição
Tabela de junção N:N entre [[pedidos_compra]] e [[notas_entrada]] — modela que 1 pedido pode ter N notas (compra dividida) e 1 nota pode cobrir N pedidos. É o vínculo "oficial", frente ao campo legado `pedidos_compra.nota_entrada_id` (ver achado em [[pedidos_compra]]).

## Confirmado no código
- Modelo: `produtos_compras_models.py:91-118` (`PedidoCompraNotaEntrada`).
- `UniqueConstraint(tenant_id, pedido_compra_id, nota_entrada_id)`.

## Relacionamentos
- FKs de saída: `pedido_compra_id → pedidos_compra.id`, `nota_entrada_id → notas_entrada.id`, `user_id → users.id`.
- Relationships: `pedido` (back_populates `PedidoCompra.notas_entrada_vinculos`), `nota` (back_populates `NotaEntrada.pedidos_compra_vinculos`).

## Utilizado por
- Leitura confirmada: `compras_pendencias_notas.py:100-103` (`nota.pedidos_compra_vinculos`).
- ❓ Escrita (INSERT) não confirmada linha a linha — presumivelmente `notas_entrada/upload_routes.py`/`sefaz_importer.py` ao vincular NF-e a um pedido.

## Não identificado
- ❓ Ponto exato de escrita não confirmado nesta pesquisa.
