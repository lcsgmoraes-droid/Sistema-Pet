# Cancelamento com lotes de origem — DEV

## Problema e comportamento

O cancelamento comum devolvia o saldo agregado, deixando os lotes consumidos
com a quantidade reduzida. O movimento de retorno também usava o custo atual
do cadastro. Isso permitia saldo físico diferente da soma rastreável dos lotes
e alterava o valor do retorno quando o custo mudava depois da venda.

O cancelamento passa a preparar todos os itens antes da primeira alteração,
travar produtos, saídas e lotes e recompor a composição original na mesma
transação do estoque e dos efeitos financeiros. O retorno registra a linha
da venda, a composição dos lotes e o custo histórico comprovado da saída.
Não executa um novo FIFO no cancelamento e não recalcula a saída original.

Linhas repetidas do mesmo SKU são agrupadas para conferir quantidades e
origem. Cada entrada mantém a atribuição rastreável de sua linha. Uma
atribuição de custo ambígua permanece desconhecida; o total de várias
saídas não é rateado cegamente entre linhas com custos diferentes.

## Limites e compatibilidade

- Produção permanece sem deploy. Não há alteração de preços nem envio ao iFood.
- O piloto 018631.1 mantém suas guardas próprias; o SKU 227 não amplia a ponte
  de pedidos nem libera outros produtos na sincronização automática.
- O custo canônico usado é o valor efetivamente registrado na baixa, incluindo
  eventual override histórico. Este trabalho não altera a valoração da saída
  para somar preços dos lotes e não reprocessa o CMV passado.
- Custo desconhecido permanece `NULL`; zero exige evidência explícita e
  consistente. Não substitui ausência pelo custo atual do cadastro.
- Histórico offline sem saída, prova ou lotes mantém a compatibilidade de
  devolução agregada, com custo desconhecido. Pedido online sem baixa
  comprovada não recebe entrada física ao cancelar.
- Retorno fiscal legado já executado não gera uma segunda entrada. Se houver
  lote, prova ou histórico conflitantes, exige conciliação antes de cancelar.
- Lote ausente, de outra empresa, prova contraditória e quantidade sem origem
  suficiente retornam conflito e preservam a transação inteira. Não há reparo
  automático de divergências antigas nem recomposição pela composição atual
  de um kit virtual.
- Quantidade não positiva ou não finita e saldo físico desconhecido/não finito
  são recusados antes do estorno. Saldo negativo conhecido permanece válido.
- A recomposição física não libera lote bloqueado ou vencido.

## Validação e roteiro

Os testes usam dados fictícios e banco PostgreSQL local descartável com schema
aleatório, além do runtime DEV já usado para o SKU 227. A API externa permanece
bloqueada no worker; os envios do ensaio usam apenas servidor HTTP em loopback.

1. Registrar estoque físico, reservas, preços e saldos/custos de cada lote.
2. Criar uma venda que consuma mais de um lote e conferir as saídas e provas.
3. Finalizar sem nova baixa; cancelar e comparar cada lote com o estado inicial.
4. Conferir que a entrada usa o custo original e não o custo atual.
5. Repetir o cancelamento e verificar ausência de nova movimentação/envio.
6. Registrar reposição em lote novo e conferir os anteriores e todos os preços.
7. Conferir reserva/liberação, concorrência, rollback e isolamento entre empresas.

Validação local concluída:

- 47 testes unitários novos; 155 testes focados passaram com as regressões.
- 16 testes novos em PostgreSQL real, incluindo campos NULL/NaN/infinito e
  quantidade Numeric NaN persistidos no banco, com conflito e rollback.
- A rodada conjunta anterior de 52 cenários passou. O CI foi ampliado para
  executar os 37 cenários da ponte, sete de estoque e os 16 novos de lotes.
- Runtime DEV: saldo 23, venda de seis unidades consumindo dois lotes, saldo
  17; cancelamento recompôs quatro unidades no primeiro lote e duas no segundo,
  voltando a 23. Repetição foi recusada sem nova entrada. Reposição em lote
  novo levou o saldo a 25, preservando os lotes anteriores e todos os preços.
- O retorno e a prova mantiveram o custo real da saída. Registros anteriores,
  pedido 1420 e produtos/empresa de controle permaneceram iguais.
- Três PATCHes somente de estoque contra simulador HTTP local. Nenhuma chamada
  ao iFood real; configuração privada e flags da API permaneceram desligadas.

Resultados detalhados e evidências do runtime ficam fora do Git; não versionar
credenciais, composes privados, dumps ou dados de clientes. Gate completo e CI
do head final devem ser conferidos no PR 1561 antes de qualquer publicação.
Guia de implantação atualizado em `docs/GUIA_INTEGRACAO_IFOOD.md`.

Rollback de publicação: manter a automação desligada e reverter o código pelo
fluxo Git autorizado; preservar saídas, entradas e provas já gravadas. Não
apagar o histórico nem executar um estorno manual duplicado.
