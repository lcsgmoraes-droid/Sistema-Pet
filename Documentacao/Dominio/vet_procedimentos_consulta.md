---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_procedimentos_consulta

Ver [[vet_consultas]], [[vet_catalogo_procedimentos]], [[ContaReceber]], [[estoque_movimentacoes]], [[vet_partner_link]], [[Produto]].

## Definição
Procedimento efetivamente realizado numa consulta — **ponto de integração real do módulo veterinário com estoque e financeiro**.

## Confirmado no código
- Modelo: `veterinario_models.py:582-607` (`ProcedimentoConsulta`).
- Colunas: `insumos` (JSON — cada item tem `produto_id` como referência **não-FK**, resolvida em runtime contra `Produto`), `estoque_baixado` (bool), `estoque_movimentacao_ids` (JSON).
- **Fluxo de baixa de estoque confirmado** (`veterinario_financeiro.py:196-309`): `_aplicar_baixa_estoque_procedimento` consome [[produto_lotes|ProdutoLote]] (FEFO) e gera [[estoque_movimentacoes|EstoqueMovimentacao]] reais para cada insumo com `produto_id`, marcando `estoque_baixado=True`. Roda quando o procedimento é marcado `realizado=True` e ainda não baixado.
- **Fluxo financeiro confirmado** (`veterinario_financeiro.py:440-570`): `_sincronizar_financeiro_procedimento` cria [[ContaReceber]] **diretamente** (não [[Venda]]!) por procedimento realizado, com `documento` único idempotente (`VET-PROC-{id}-...`). Se o tenant é "parceiro" (via [[vet_partner_link]]), gera **duas** contas a receber: uma para o vet (receita líquida) e outra para a empresa dona da loja (repasse/comissão).

## Relacionamentos
- FKs de saída: `consulta_id → vet_consultas.id`, `catalogo_id → vet_catalogo_procedimentos.id` (nullable), `user_id → users.id`.
- `insumos.produto_id` referencia informalmente `produtos.id`, sem FK real (diferente de [[vet_orcamento_itens]], que tem FK real).

## Utilizado por
- `veterinario_financeiro.py` (baixa de estoque e geração financeira).

## Não identificado
- ⚠️ **Achado central deste módulo**: consulta/procedimento veterinário **não passa pelo módulo de Vendas** — gera conta a receber e baixa estoque diretamente, sem criar registro de [[Venda]]. Vale ter isso em mente para qualquer relatório que agregue vendas do sistema — procedimentos vet ficam de fora se a query filtrar só por `vendas`.
- Inconsistência de modelagem: `insumos.produto_id` é JSON solto aqui, mas é FK real em [[vet_orcamento_itens]] — duas tabelas semanticamente parecidas com padrões de referência diferentes.
