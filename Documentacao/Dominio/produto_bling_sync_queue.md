---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_bling_sync_queue

Ver [[produto_bling_sync]], [[produto_bling_cost_sync_queue]], [[Bling]].

## Definição
Fila outbox de sincronização de **estoque** de produto para o Bling (ERP externo) — persistente, com retry.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:477-504` (`ProdutoBlingSyncQueue`).
- Colunas: `produto_id`, `sync_id`, `estoque_novo`, `motivo`, `origem`, `status` (pendente/processando/sucesso/erro/falha_final), `forcar_sync`, `tentativas`, `ultima_tentativa_em`/`proxima_tentativa_em`, `processado_em`, `ultimo_erro`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id`, `sync_id → produto_bling_sync.id`.
- Referenciada por: `Produto.bling_sync_queue_items`, `ProdutoBlingSync.fila` (cascade all, delete-orphan).

## Utilizado por
- `services/bling_sync_queue.py` (`queue_product_sync`, `_mark_success`, linhas 159-246) — implementação da fila.
- `services/bling_sync_auto_link.py`, `services/bling_sync_reconciliation.py`, `services/bling_sync_reprocess.py`, `services/bling_sync_shared.py`, `services/produto_merge_safety.py`.

## Não identificado
- Nada notável — padrão de fila outbox clássico.
