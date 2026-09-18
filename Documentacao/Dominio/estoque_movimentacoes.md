---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — estoque_movimentacoes

Ver [[Produto]], [[produto_lotes]], [[Venda]], [[estoque_validade_bloqueios]].

## Definição
Tabela central do módulo de estoque: todo ajuste de quantidade de um produto (entrada, saída, transferência) gera uma linha aqui, com snapshot de quantidade antes/depois. É o livro-razão do estoque.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:361-439` (`EstoqueMovimentacao`).
- Colunas-chave: `produto_id`, `tipo` (entrada/saida/transferencia), `motivo` (compra/venda/ajuste/devolucao/perda/transferencia/balanco), `quantidade`, `quantidade_anterior`/`quantidade_nova`, `custo_unitario`, `valor_total`, `lote_id` (lote principal), `lotes_consumidos` (⚠️ JSON serializado manualmente em coluna `Text`, não `JSON` tipado), `estoque_origem`/`estoque_destino` (string livre, não FK), `documento`, `referencia_id`+`referencia_tipo` (⚠️ FK polimórfica não tipada — venda/compra/ajuste/procedimento_veterinario, sem integridade referencial no banco), `status` (reservado/confirmado/cancelado), `user_id`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id`, `lote_id → produto_lotes.id` (nullable), `user_id → users.id`.
- Referenciada por: `estoque_validade_bloqueios.movimentacao_bloqueio_id` e `.movimentacao_resolucao_id`.
- Relationship reverso: `Produto.movimentacoes` (sem cascade delete-orphan, diferente das demais relações de Produto).

## Utilizado por
- Escrita central: `app/estoque/service.py` — `EstoqueService.baixar_estoque` (linha 408) e `EstoqueService.estornar_estoque` (linha 543).
- Leitura ampla: `routes/app_mobile_funcionario_contagem_routes.py`, `routes/app_mobile_funcionario_estoque_routes.py`, `services/bling_flow_monitor_diagnostics_parts/inventory.py`, `services/bling_nf/desvinculo.py`, `services/bling_nf/estoque.py`.

## Não identificado
- ⚠️ `referencia_id`/`referencia_tipo` é FK polimórfica sem integridade referencial.
- ⚠️ `lotes_consumidos` em `Text` (JSON manual) em vez de coluna `JSON` nativa — inconsistente com [[estoque_fracionamento_conversoes]], que usa `JSON` corretamente.
- `status="reservado"` sugere suporte a reserva de estoque antes da confirmação fiscal — mecânica completa não aprofundada.
