---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_bling_cost_sync_queue

Ver [[produto_bling_sync_queue]], [[Produto]], [[Bling]].

## Definição
Fila outbox de sincronização de **custo/preço de fornecedor** de produto para o Bling — paralela e independente da fila de estoque ([[produto_bling_sync_queue]]), mesmo parceiro externo, propósito diferente.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:507-548` (`ProdutoBlingCostSyncQueue`).
- Colunas: `produto_id` (unique junto com `tenant_id` — só 1 pendência de custo por produto por vez), `preco_custo_novo`, `bling_produto_fornecedor_id`, `motivo`, `origem`, `status`, `forcar_sync`, `versao` (controle otimista), `tentativas`, timestamps de retry, `ultimo_custo_enviado`, `ultimo_erro`.

## Relacionamentos
- FK de saída: `produto_id → produtos.id` (CASCADE).
- Sem referências reversas de outras tabelas.

## Utilizado por
- `services/bling_cost_sync_service.py` (`queue_product_cost_sync`, linhas 152-215).
- `services/produto_merge_safety.py`.

## Não identificado
- Nada notável.
