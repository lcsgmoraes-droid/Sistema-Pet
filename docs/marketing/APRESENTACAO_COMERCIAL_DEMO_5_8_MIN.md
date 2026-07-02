# Apresentacao Comercial Demo 5 a 8 Min - Sistema Pet

Uso: roteiro principal para gravar uma apresentacao consultiva do Sistema Pet
usando a base local `corepeterp@gmail.com`.

Ambiente:

- URL local: `http://127.0.0.1:5173/login`
- Usuario: `corepeterp@gmail.com`
- Senha local: `12345678`
- Base validada: vendas, financeiro, produtos, calculadora de racao,
  comissoes, entregas e RH.

## Objetivo da apresentacao

Mostrar que o Sistema Pet conecta venda, estoque, financeiro, entrega,
comissao e decisao gerencial em uma rotina unica.

Mensagem central:

```text
O Sistema Pet nao e so uma tela de venda.
Ele ajuda o gestor a enxergar o caminho completo: produto, venda, recebimento,
estoque, entrega, comissao, custo e resultado.
```

## Preparacao antes de gravar

1. Abrir `http://127.0.0.1:5173/login`.
2. Logar com `corepeterp@gmail.com`.
3. Fechar abas pessoais e notificacoes.
4. Usar zoom entre 90% e 100%.
5. Comecar pela tela `/financeiro/vendas`.
6. Nao comecar pelo dashboard financeiro, porque ele mostra alerta de risco; usar esta tela depois para falar de controle.

## Versao curta - 5 minutos

| Tempo | Tela | Objetivo | Acao na tela |
|---:|---|---|---|
| 0:00-0:30 | `/financeiro/vendas` | Abrir com a visao de resultado | Mostrar totais e Lista de Vendas |
| 0:30-1:20 | `/financeiro/vendas` | Mostrar venda completa | Dar zoom em desconto, imposto, CMV, lucro, margem e status |
| 1:20-2:00 | `/produtos` | Mostrar produto/estoque | Mostrar produtos reais com imagem, custo, margem, preco e estoque |
| 2:00-2:40 | `/calculadora-racao` | Mostrar diferencial consultivo | Peso 12kg, idade 36, Comparar Todas |
| 2:40-3:20 | `/financeiro/contas-receber` | Mostrar recebimentos | Mostrar venda aberta, previsao e recebimento efetivo |
| 3:20-4:00 | `/entregas/rotas` | Mostrar entrega | Mostrar rota pendente e rota em andamento |
| 4:00-4:35 | `/comissoes/abertas` | Mostrar comissao | Mostrar Beatriz, 8 comissoes e total pendente |
| 4:35-5:00 | `/financeiro` | Fechar com gestao | Mostrar leitura automatica e alertas |

## Versao completa - 8 minutos

| Tempo | Tela | Objetivo | Acao na tela |
|---:|---|---|---|
| 0:00-0:40 | `/financeiro/vendas` | Gancho: resultado real da venda | Mostrar cards e filtros |
| 0:40-1:30 | `/financeiro/vendas` | Explicar venda por canal | Mostrar ERP/PDV, ecommerce, aberta, baixada e campanha |
| 1:30-2:10 | `/produtos` | Mostrar cadastro de produto | Mostrar imagem, custo, margem, preco, estoque e canais |
| 2:10-3:00 | `/calculadora-racao` | Mostrar venda consultiva | Comparar racoes por custo/dia, custo/mes e preco/kg |
| 3:00-3:45 | `/financeiro/contas-receber` | Mostrar previsao e recebimento | Explicar venda recebida, parcial e em aberto |
| 3:45-4:30 | `/financeiro/contas-pagar` | Mostrar custos operacionais | Mostrar imposto, taxa, entrega, comissao, despesas fixas |
| 4:30-5:10 | `/financeiro/fluxo-caixa` | Mostrar previsto x realizado | Mostrar entradas, saidas e vencimentos |
| 5:10-5:50 | `/financeiro/dre` | Mostrar resultado gerencial | Explicar receita, CMV, impostos, despesas e resultado |
| 5:50-6:30 | `/entregas/rotas` | Mostrar processo de entrega | Mostrar Carlos Entregador Demo e rotas |
| 6:30-7:10 | `/comissoes` e `/comissoes/abertas` | Mostrar regra e pagamento | Mostrar Beatriz com regra geral e comissoes pendentes |
| 7:10-7:40 | `/financeiro` | Mostrar alerta executivo | Mostrar leitura automatica, contas vencidas e risco |
| 7:40-8:00 | Tela com melhor visual do momento | CTA | Encerrar com chamada para demonstracao |

## Roteiro de fala

### Abertura - 0:00 a 0:30

Tela: `/financeiro/vendas`

```text
Aqui eu gosto de comecar porque essa tela mostra o que acontece depois que a loja vende.
Nao e so total de venda. O sistema mostra canal, desconto, taxa, imposto, custo,
comissao, valor recebido, lucro e margem.
```

Movimento:

- Abrir `Lista de Vendas`.
- Passar o mouse pelos totais.
- Dar zoom em `Venda Bruta`, `Liquida`, `Valor Recebido`, `Custo`, `Lucro` e `Margem`.

### Venda completa - 0:30 a 1:30

Tela: `/financeiro/vendas`

```text
Cada linha conta uma historia.
Tem venda baixada, venda em aberto, ecommerce, app, campanha, entrega e pagamento.
Isso ajuda o gestor a entender nao apenas quanto vendeu, mas quanto sobrou em cada operacao.
```

Movimento:

- Mostrar uma venda baixada.
- Mostrar uma venda aberta.
- Mostrar coluna de imposto, comissao, custo e margem.
- Se for corte curto, focar em uma venda so.

### Produto e estoque - 1:30 a 2:10

Tela: `/produtos`

```text
Antes da venda fazer sentido, o produto precisa estar bem cadastrado.
Aqui aparecem produtos reais, com imagem, custo, preco, margem, estoque e canais
onde ele pode ser vendido.
```

Movimento:

- Mostrar 2 ou 3 produtos com imagem.
- Dar zoom em custo, margem, preco de venda, estoque e canais `E-commerce`/`App`.

### Comparador de racao - 2:10 a 3:00

Tela: `/calculadora-racao`

```text
Esse e um diferencial bem forte para loja pet.
Nem sempre o pacote mais barato e o melhor para o cliente.
Na calculadora, a loja compara racoes por consumo diario, duracao do pacote,
custo por mes e preco por quilo.
```

Movimento:

1. Preencher peso `12`.
2. Preencher idade `36`.
3. Clicar em `Comparar Todas`.
4. Mostrar `Melhor Custo-Beneficio`.
5. Dar zoom em `Custo/dia`, `Custo/mes`, `Duracao` e `Preco/kg`.

### Recebimentos - 3:00 a 3:45

Tela: `/financeiro/contas-receber`

```text
Quando a venda acontece, o financeiro precisa acompanhar o que ja foi recebido
e o que ainda esta previsto.
Isso evita aquele caixa misturado entre PIX, dinheiro, cartao, prazo e venda em aberto.
```

Movimento:

- Mostrar contas recebidas.
- Mostrar previsao/em aberto.
- Explicar que forma de pagamento e banco precisam estar configurados antes da venda.

### Contas a pagar e custos - 3:45 a 4:30

Tela: `/financeiro/contas-pagar`

```text
Do outro lado estao os custos.
Taxa de cartao, custo de entrega, comissao, impostos, folha e despesas fixas
precisam entrar na conta para o resultado ficar real.
```

Movimento:

- Mostrar categorias de despesas.
- Passar por impostos, comissoes e entregas.
- Evitar abrir detalhes com informacao desnecessaria.

### Fluxo, DRE e ponto de decisao - 4:30 a 5:50

Telas: `/financeiro/fluxo-caixa` e `/financeiro/dre`

```text
Depois que vendas, recebimentos e despesas estao conectados, o gestor consegue
olhar fluxo de caixa e DRE com mais seguranca.
O objetivo e saber o que entrou, o que saiu, o que esta previsto e como isso
impacta o resultado.
```

Movimento:

- No fluxo, mostrar previsto x realizado.
- Na DRE, mostrar receita, CMV, impostos, despesas e resultado.

### Entregas - 5:50 a 6:30

Tela: `/entregas/rotas`

```text
Venda com entrega nao termina no caixa.
Ela precisa virar rota, ter entregador, status e custo para a operacao.
Aqui a entrega entra na mesma historia da venda e do financeiro.
```

Movimento:

- Mostrar Carlos Entregador Demo.
- Mostrar `DEMO-ROT-002` em rota e `DEMO-ROT-003` pendente.
- Nao falar em rastreio ao vivo se nao houver localizacao ativa.

### Comissoes - 6:30 a 7:10

Telas: `/comissoes` e `/comissoes/abertas`

```text
Se a loja trabalha com vendedor comissionado, a regra precisa estar clara.
Aqui a Beatriz tem regra geral cadastrada, e depois das vendas o sistema mostra
as comissoes pendentes para conferencia.
```

Movimento:

- Mostrar Beatriz com 1 regra geral.
- Ir para `/comissoes/abertas`.
- Mostrar 8 comissoes e total pendente.

### Fechamento executivo - 7:10 a 8:00

Tela: `/financeiro`

```text
No fim, o sistema ajuda o gestor a enxergar sinais importantes.
Se o caixa esta pressionado, se existem contas vencidas, se os recebimentos
cobrem as saidas e onde precisa de atencao.
O Sistema Pet organiza a rotina para a loja vender, entregar, controlar e decidir melhor.
```

CTA:

```text
Se voce quer ver sua operacao pet com venda, estoque, financeiro, entrega e
resultado no mesmo fluxo, peca uma demonstracao do Sistema Pet.
```

## Cortes curtos derivados

| Corte | Origem | Duracao | Gancho |
|---|---|---:|---|
| Lucro real | `/financeiro/vendas` | 20s | "Vender muito nao significa lucrar." |
| Racao com argumento | `/calculadora-racao` | 25s | "A racao barata no pacote e barata por dia?" |
| Recebimento organizado | `/financeiro/contas-receber` | 20s | "PIX, cartao e dinheiro no mesmo bolo?" |
| Entrega com custo | `/entregas/rotas` | 25s | "Entrega saiu, mas entrou no financeiro?" |
| Comissao clara | `/comissoes/abertas` | 20s | "Comissao sem planilha paralela." |

## Checklist do video aprovado

- A tela inicial e `/financeiro/vendas`.
- Nenhum dado real aparece.
- A narracao nao promete aumento garantido de venda ou lucro.
- O comparador de racao mostra custo/dia coerente.
- Entregas nao prometem rastreio ao vivo sem localizacao.
- O dashboard financeiro e usado como controle/alerta, nao como primeira impressao.
- O CTA final convida para demonstracao.
