---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Compras

Ver [[Funcionalidades]], [[Produtos-Estoque]], [[Bling]].

## Identificação

- **Menu:** Estoque e suprimentos → Compras (submenu: Pedidos, Central NF-e Entradas, Pendências)
- **Rota frontend:** `/compras`
- **Módulo de rota:** `frontend/src/app/routes/PurchasingBlingRoutes.jsx` (compartilhado com rotas Bling — `/vendas/bling-*`)

## Objetivo

Pedido de compra a fornecedores, entrada de nota fiscal (XML), e monitoramento de pendências de importação/sincronização com o Bling.

## Backend (confirmado)

`bling_sync_routes.py`, `pedidos_compra_routes.py`, `fornecedor_grupos_routes.py`, `notas_entrada_routes.py`, `compras_pendencias_routes.py`.

## Banco de dados

`PedidoCompra`, `PedidoCompraItem`, `NotaEntrada`, `NotaEntradaItem` (`produtos_compras_models.py`).

## Segurança

Upload de XML de nota de entrada sem limite de tamanho confirmado — ver [[Vulnerabilidades]] item 4 e [[API-Security]].

## Dependências

[[Produtos-Estoque]] (destino do estoque comprado), [[Cliente]] (fornecedor), [[Bling]] (sincronização).

## Não identificado

- Nenhum achado adicional além dos já cobertos em [[Produtos-Estoque]] e [[Bling]].
