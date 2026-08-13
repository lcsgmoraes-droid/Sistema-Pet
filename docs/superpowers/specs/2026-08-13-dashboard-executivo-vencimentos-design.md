# Dashboard executivo e vencimentos por data

## Objetivo

Transformar a abertura do dashboard em uma leitura executiva rápida e corrigir a classificação de contas para que um lançamento com vencimento na data atual nunca seja apresentado como vencido.

## Decisões de produto

- O cabeçalho deixa de ser um card alto. Título, situação, horário da atualização, período e ações ficam em uma faixa compacta.
- O primeiro bloco mostra três resultados principais do período:
  - faturamento;
  - pedidos e unidades vendidas;
  - lucro das vendas.
- O card de lucro abre a DRE. Faturamento e pedidos/unidades abrem a consulta de vendas.
- O segundo bloco mostra apenas posições úteis para decisão imediata:
  - saldo em bancos;
  - resultado de caixa do período;
  - ticket médio;
  - total a receber;
  - total a pagar.
- Pendências continuam em uma área separada. Pagamentos vencidos e pagamentos que vencem hoje serão apresentados em cards distintos.
- Gráficos, ranking de produtos, clientes e listas de contas permanecem abaixo da leitura executiva.

## Regra de vencimento

A referência é o dia civil de Brasília, sem considerar a hora:

- vencido: `data_vencimento < hoje`;
- vence hoje: `data_vencimento == hoje`;
- a vencer: `data_vencimento > hoje`.

O dashboard não usará o horário atual para comparar uma coluna de data. Contas abertas com status `pendente`, `parcial`, `vencido` ou `vencida` participam da classificação; a data define em qual grupo aparecem.

## Dados e fluxo

O endpoint leve `GET /dashboard/resumo` continuará sendo a fonte da abertura do painel e será enriquecido com:

- `contas_pagar.vence_hoje`;
- `contas_receber.vence_hoje`;
- `vendas_periodo.unidades`;
- `vendas_periodo.lucro`.

Unidades serão a soma das quantidades dos itens das vendas não canceladas no período. O lucro das vendas será lido do snapshot de rentabilidade já consolidado em cada venda. Quando uma venda antiga não tiver snapshot, o dashboard não fará reprocessamento pesado nem alterará dados durante uma simples consulta; o valor ausente será tratado como zero e o relatório de vendas seguirá sendo o local de reprocessamento detalhado.

Resultado de caixa permanece separado do lucro das vendas: entradas menos saídas não será rotulado como lucro comercial.

## Componentes

- `DashboardFinanceiro`: composição, navegação e carregamento dos blocos.
- `DashboardCards`: cards principais e cards compactos de posição.
- `dashboardOverview`: valores padrão, normalização e indicadores derivados.
- `dashboard_routes`: consolidação leve e regras de datas.

## Falhas e estados vazios

- Se um bloco secundário falhar, o painel mantém os demais resultados e informa quais dados não foram atualizados.
- Valores ausentes aparecem como zero; saldo bancário mantém o fallback estimado já existente.
- Sem vendas, faturamento, pedidos/unidades e lucro aparecem zerados sem indicar falsamente que a operação está saudável.

## Validação

- Teste de backend comprovando que conta vencida ontem entra em vencidos, conta de hoje entra em vence hoje e conta futura não entra em nenhum desses dois grupos.
- Teste do contrato do resumo para unidades e lucro das vendas.
- Teste das funções de indicadores do frontend.
- Teste estrutural da composição do dashboard para os três cards principais e navegação para DRE.
- Lint focado, testes do dashboard e build de produção do frontend.
- Conferência visual em largura desktop e responsiva antes de solicitar publicação.

## Fora do escopo

- Não será criada comparação simultânea entre vários períodos como no painel de marketplace da referência.
- Não haverá mudança na DRE, no relatório completo de vendas ou nos lançamentos financeiros.
- Não haverá deploy em produção sem nova autorização explícita do Lucas.
