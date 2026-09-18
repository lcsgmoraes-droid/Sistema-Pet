---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — pedidos_integrados_itens

Ver [[pedidos_integrados]].

## Definição
Item de um [[pedidos_integrados|pedido integrado]] — "responsável pela reserva de estoque" (docstring).

## Confirmado no código
- Modelo: `pedido_integrado_item_models.py:6-25` (`PedidoIntegradoItem`).
- Colunas: `sku`, `descricao`, `quantidade`, `reservado_em`, `liberado_em`, `vendido_em` — ⚠️ **máquina de estados por timestamp**, não há coluna `status` textual; o estado é inferido por quais datas estão preenchidas (item "ativo" = `liberado_em IS NULL AND vendido_em IS NULL`).

## Relacionamentos
- FK de saída: `pedido_integrado_id → pedidos_integrados.id`.
- Sem referências de entrada.

## Utilizado por
- `estoque_reserva_service.py` — `reservar()`, `liberar()`, `confirmar_venda()`.

## Não identificado
- Nada notável — padrão de máquina de estados por timestamp é incomum mas bem implementado e consistente.
