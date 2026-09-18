---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — estoque_validade_bloqueios

Ver [[Produto]], [[produto_lotes]], [[estoque_movimentacoes]].

## Definição
Materializa o bloqueio de um lote vencido/a vencer, ligando-se de volta a [[estoque_movimentacoes]] para rastrear o efeito contábil tanto do bloqueio quanto da resolução (troca com fornecedor, descarte, retorno ao vendável).

## Confirmado no código
- Modelo: `estoque_validade_models.py:7-49` (`EstoqueValidadeBloqueio`).
- Colunas: `produto_id`, `lote_id` (NOT NULL — diferente de `campanha_validade_exclusoes.lote_id`, que é nullable), `user_id` (nullable), `status` (default `"pendente"`), `origem` (default `"rotina"`), `data_referencia`, `data_validade`, `quantidade_bloqueada`/`quantidade_resolvida`, `custo_unitario`, `custo_total_estimado`, `movimentacao_bloqueio_id`, `movimentacao_resolucao_id`, `decidido_por_user_id`, `decidido_em`, `decisao`, `observacao`.

## Relacionamentos
- FKs de saída: `produto_id → produtos.id`, `lote_id → produto_lotes.id`, `user_id`/`decidido_por_user_id → users.id`, `movimentacao_bloqueio_id`/`movimentacao_resolucao_id → estoque_movimentacoes.id` (bidirecional: uma FK para a movimentação que gerou o bloqueio, outra para a que resolveu).
- Sem referências reversas de outras tabelas.

## Utilizado por
- `app/estoque_validade_service.py` (`bloquear_lote` linha 44-113, `descartar_bloqueio`, `processar_lotes_em_risco`, `trocar_com_fornecedor`, `retornar_ao_vendavel`).
- `app/estoque_validade_routes.py`.

## Não identificado
- Nada notável.
