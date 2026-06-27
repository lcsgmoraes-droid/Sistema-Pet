# Entrada XML - Movimentos Pendentes Apos NF Lancada

## Objetivo

Permitir que uma NF de entrada ja cadastrada ou conciliada receba movimentos que ficaram para depois, sem duplicar estoque, custo, preco de venda ou financeiro ja lancados.

## Regra Principal

O sistema deve tratar cada acao do processamento de forma independente:

- `lancar_estoque`
- `atualizar_custo`
- `atualizar_preco_venda`
- `gerar_contas_pagar`

Ao abrir a revisao/processamento de uma NF, o backend deve informar quais acoes ja foram realizadas e quais ainda estao pendentes. A tela pode mostrar as mesmas opcoes, mas acoes ja realizadas ficam bloqueadas e nao podem ser enviadas de novo.

## Fluxo de Tela

Em uma NF pendente, o fluxo continua igual: revisar acoes, confirmar e processar.

Em uma NF ja conciliada/processada, deve existir um caminho visivel para abrir `Lancar movimentos pendentes`. A tela reutiliza a revisao atual, mostra os checkboxes, bloqueia o que ja foi lancado e deixa o usuario marcar apenas o que ainda pode ser lancado.

## Protecao Contra Duplicidade

Mesmo que a tela esteja desatualizada, o backend deve rejeitar tentativa de relancar uma acao ja realizada. Se nenhuma acao pendente for selecionada, a resposta deve explicar que nao ha movimento pendente selecionado.

## Sem Nova Tabela

A primeira versao deve reaproveitar os registros existentes:

- estoque por `estoque_movimentacoes` da nota;
- financeiro por `contas_pagar.nota_entrada_id`;
- custo/preco por `processamento_acoes` e historico de preco quando existir.

O campo `processamento_acoes` passa a representar o acumulado das acoes ja realizadas para aquela NF.
