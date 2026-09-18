---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_bling_sync

Ver [[Produto]], [[produto_bling_sync_queue]], [[Bling]].

## Definição
Estado de sincronização de estoque de um produto com o Bling (ERP externo) — 1:1 com [[Produto]].

## Confirmado no código
- Modelo: `produtos_estoque_models.py:442-474` (`ProdutoBlingSync`).
- Colunas: `produto_id` (**unique**, 1:1 com Produto), `bling_produto_id`, `retirado_para_produto_id` (auto-referência a `produtos.id` — comentário linha 451: identidade histórica preservada para pedidos antigos, nunca publicador de estoque ativo, apesar do nome sugerir o contrário), `sincronizar`, `estoque_compartilhado`, timestamps de tentativa/sucesso, `tentativas_sync`, `ultimo_estoque_bling`, `ultima_divergencia`, `status` (ativo/pausado/erro).

## Relacionamentos
- FKs de saída: `produto_id → produtos.id` (unique), `retirado_para_produto_id → produtos.id` (nullable).
- Referenciada por: [[produto_bling_sync_queue]].`sync_id`. Relationship `Produto.bling_sync` (uselist=False) e `.fila` (cascade all, delete-orphan).

## Utilizado por
- `services/produto_bling_identity_service.py` (serviço dedicado à lógica de "produto retirado/substituído", linhas 14-81).
- `services/bling_sync_auto_link.py:87`, `services/bling_sync_reprocess.py:123`, `services/produto_merge_service.py:378`.

## Não identificado
- Nome do campo `retirado_para_produto_id` é ambíguo (sugere "para onde foi retirado o estoque", mas na prática é identidade histórica, não estoque ativo) — vale checar com o time se o nome deveria mudar.
