# Reprocessar Custos de Vendas - Design

## Objetivo

Permitir que Lucas corrija o custo cadastrado de um produto e reprocesse manualmente vendas antigas para que custo, lucro e margem passem a refletir o custo atual do cadastro.

## Regra Principal

O reprocessamento manual usa o `Produto.preco_custo` atual. Quando a venda tiver movimentacao de estoque vinculada, a movimentacao tambem deve receber o custo atual:

- `EstoqueMovimentacao.custo_unitario = Produto.preco_custo`
- `EstoqueMovimentacao.valor_total = abs(EstoqueMovimentacao.quantidade) * Produto.preco_custo`

Depois disso, o snapshot de rentabilidade da venda deve ser recriado com `force_refresh=True`, usando esses custos corrigidos.

## Escopo

Incluido:

- Reprocessar uma venda individual.
- Reprocessar vendas selecionadas na lista.
- Reprocessar o periodo atualmente filtrado no relatorio.
- Confirmar antes da acao, informando quantas vendas serao reprocessadas.
- Melhorar a rolagem horizontal da tabela de vendas para ficar acessivel tambem no topo.

Fora do escopo:

- Alterar quantidade de estoque.
- Alterar pagamentos, caixa, contas a receber, cliente, NF ou status da venda.
- Reprocessar automaticamente vendas sem acao manual.

## Interface

A lista tera checkbox por linha e um unico botao de acoes de reprocessamento no cabecalho da lista. O botao abre opcoes:

- Reprocessar selecionadas.
- Reprocessar periodo atual.

Cada linha tambem tera uma acao discreta para reprocessar aquela venda, sem multiplicar botoes de lote.

## API

Criar endpoint autenticado em `/relatorios/vendas/reprocessar-rentabilidade`.

O corpo aceita:

- `venda_ids`: lista opcional de IDs.
- `data_inicio` e `data_fim`: periodo opcional.
- `canal_venda`: filtro opcional.

O endpoint valida tenant, ignora vendas canceladas e retorna resumo com total solicitado, total reprocessado e vendas afetadas.

## Testes

- Teste unitario do servico garantindo que a movimentacao e o snapshot usam o custo atual.
- Teste unitario/contrato do endpoint garantindo filtro por tenant e escopo por IDs/periodo.
- Build frontend para validar integracao da tela.
