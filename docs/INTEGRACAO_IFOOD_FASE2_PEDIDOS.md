# Integracao iFood - Fase 2: pedidos e homologacao

## Objetivo

Preparar o CorePet para a homologacao da categoria **Groceries**, usada por
mercados, farmacias e pet shops. Esta fase nao libera envio de produtos.

## Modulos solicitados no aplicativo

- `merchant`: identificacao e configuracao da loja.
- `item`: catalogo, preco e estoque de Groceries.
- `events`: recebimento e acknowledgment de eventos.
- `order`: consulta e ciclo de vida dos pedidos.
- `picking`: separacao de itens para pedidos de mercado/pet shop.

Modulos financeiros, analytics, shipping e logistica externa ficam fora do
escopo inicial.

## Fluxos implementados

1. Polling de eventos com filtro pelo Merchant ID da empresa.
2. Persistencia idempotente do evento antes do acknowledgment.
3. Consulta e armazenamento do pedido pela Orders Virtual Bag
   (`GET /order/v1.0/orders/{id}/virtual-bag`).
4. Exibicao de `uniqueId`, EAN, PLU, quantidade, preco e `unavailable` de cada
   item na interface do CorePet.
5. Inicio da separacao pelo modulo Picking.
6. Alteracao da quantidade separada de um item.
7. Remocao de item indisponivel.
8. Finalizacao da separacao seguida de nova consulta da Virtual Bag para
   comprovar as alteracoes.
9. Atualizacao local dos estados e registro da ultima acao executada.

A tela mostra itens, pagamento, cupons e seus responsaveis, endereco, localizador
do telefone e os controles de Picking para servir como evidencia da homologacao.

## Travas operacionais

As tres operacoes externas sao independentes:

- `IFOOD_CATALOG_WRITE_ENABLED=false`: bloqueia qualquer envio de produto.
- `IFOOD_ORDER_OPERATIONS_ENABLED=false`: bloqueia ACK e acoes de pedido.
- `IFOOD_ORDER_POLLING_ENABLED=false`: impede o polling automatico.

O polling automatico so inicia quando as duas travas de pedidos estao ativas.
O intervalo minimo e 30 segundos e apenas um worker lider executa o ciclo.

## Piloto assistido de PDV em DEV

A recepcao e o espelho do pedido sao separados da importacao no PDV. O piloto
adiciona uma acao explicita no painel de pedidos da integracao: **Enviar ao PDV
de teste**. Essa acao nao confirma, separa ou entrega o pedido no iFood.

**Estado da validacao em 24/10/2026:** o ensaio sintetico local e o fluxo do
pedido **oficial de testes #1420** foram aprovados, como evidencias separadas.
O pedido foi confirmado pela UI do iFood as 20h43; o CorePet recebeu tres eventos,
confirmou os tres (ACK) e registrou zero falhas. A importacao pela interface criou
somente a venda de teste `202610240002` (ID 2) e uma reserva de uma unidade do SKU
`018631.1`. A conclusao pela acao propria no PDV fez uma unica baixa FIFO: fisico
30 para 29, reservas 4 para 3, disponivel 26 e primeiro lote 9 para 8.

O checkout oficial foi R$ 75,89: produto R$ 65,00, frete R$ 8,90 e servico
exclusivo do iFood R$ 1,99. A venda operacional e o pagamento externo iFood
ficaram em R$ 73,90, com caixa nulo. A evidencia JSON do recebivel permaneceu
`awaiting_financial`, bruto R$ 73,90, recebido zero, liquido/data nulos e margem
pendente. Os hashes das 12 tabelas financeiras de controle nao mudaram; os
R$ 65,00 que ja constavam no caixa pertencem a venda sintetica anterior, sem nova
entrada de caixa pelo pedido oficial.

Reimportacao e repeticao da conclusao pela API nao produziram delta de venda,
reserva, pagamento ou estoque. A evidencia local
`official1420-finalization-proof.json` registrou PASS. Outras empresas, produtos
e precos de ERP/app/ecommerce foram preservados, sem alteracao em producao.
O aceite tecnico oficial e especifico deste pedido/PDV/reserva/baixa em DEV;
Financial e relatorios gerais continuam com os limites descritos abaixo.

O piloto exige todas as configuracoes abaixo, inicialmente vazias/desligadas:

- `IFOOD_PDV_PILOT_ENABLED=true`;
- `IFOOD_PDV_PILOT_TENANT_ID`: empresa ficticia do DEV;
- `IFOOD_PDV_PILOT_MERCHANT_ID`: loja oficial de testes;
- `IFOOD_PDV_PILOT_ORDER_ID`: unico pedido autorizado;
- `IFOOD_PDV_PILOT_SKU=018631.1`.

O ambiente deve ser `development`, `dev`, `test` ou `local`. Producao e staging
continuam recusados mesmo se a flag for ligada. O payload da Orders Virtual Bag
precisa declarar `test=true`, a mesma loja e pedido, um unico item de uma unidade
fixa do SKU autorizado e o mesmo EAN. Neste primeiro ensaio, sao aceitos somente
retirada (`TAKEOUT`/`TAKE-OUT`) ou entrega (`DELIVERY`) com frete explicitamente
informado e nao negativo, preco do item positivo e sem cupom ou desconto. O modo
offline aceita dinheiro presencial no total exato do item mais frete, sem taxas
adicionais. O modo online aceita um unico credito sob responsabilidade explicita
do iFood, identificador de pagamento valido e evidencia do evento oficial
recebido. Nesse modo, a unica taxa adicional aceita e a de servico paga pelo
consumidor e comprovadamente pertencente ao iFood. Frete online positivo exige
`provider=MERCHANT`. Pagamento misto, outros meios, pesagem variavel, itens
adicionais e dados desconhecidos ficam bloqueados.

A importacao cria uma venda aberta do canal `ifood` e uma reserva pelo mesmo
`PedidoIntegradoItem` utilizado nas demais integracoes. O pedido local tem
`pedido_bling_id=NULL`: ele nao e um pedido Bling. O vinculo auditavel em
`ifood_pdv_bridges` une o pedido iFood, a reserva, o produto e a venda. Repetir a
importacao retorna o vinculo existente, sem criar nova venda ou reserva.

O hash da evidencia vincula tambem frete, taxa de servico, totais e pagamento.
Divergencia nesses valores impede reaproveitar a validacao anterior. O frete nao
aumenta a quantidade reservada nem a baixa FIFO: ambas continuam restritas a uma
unidade do produto.

O online usa a acao explicita
`POST /integracoes/ifood/pedidos/{order_id}/piloto-pdv/finalizar-online`, sem
pagamentos novos no corpo. Central e PDV mostram **Concluir venda e baixar
estoque** somente com `can_finalize_online=true`. O endpoint revalida escopo,
origem, evento, pagamento e sacola; registra a quitacao externa identificada
como `iFood online` e executa a baixa uma vez, sem modal de cobranca, movimento
de caixa ou conta global dada como recebida. O modo offline conserva o fluxo
de pagamento presencial autorizado.

`pdv_bridge` e `Venda.ifood_pdv_pilot` apresentam modo, capacidade de conclusao,
checkout, pagamento e recebivel. O checkout diferencia R$ 65,00 do item,
R$ 8,90 do frete e R$ 73,90 operacionais dos R$ 1,99 de servico do iFood e
R$ 75,89 do consumidor. A evidencia JSON da ponte mantem o repasse em
`awaiting_financial`, recebido zero, liquido/data desconhecidos e margem pendente.
Nao se presume receita da loja ou repasse pelo total cobrado do consumidor.
Fora do escopo ou com modo desconhecido, a UI bloqueia cobranca manual; somente
um resumo habilitado com `payment_mode=offline` libera o dinheiro presencial.

**Pendencia P2 — relatorios gerais:** essas telas ainda nao consideram o repasse
`awaiting_financial` como uma condicao propria de margem pendente. Seus totais e
margens nao foram homologados para este piloto online e nao podem justificar
ampliacao para outros produtos/lojas ou producao. A referencia desta etapa e o
resumo do pedido com margem/repasse pendentes do Financial; o financeiro geral
nao e alterado por esta entrega.

Ao finalizar a venda no PDV, o fluxo normal faz a baixa FIFO dos lotes e encerra
a reserva na mesma transacao. Repeticoes e concorrencia nao podem executar outra
baixa. Cancelar a venda antes da finalizacao somente libera a reserva, sem
inventar uma entrada de estoque. O cancelamento remoto impede a finalizacao
depois de seu evento ser recebido e registrado no CorePet. Neste piloto, a
liberacao local exige a acao explicita **Cancelar** no PDV. Nao ha estorno
retroativo automatico por eventos do provedor.

Itens e precos da venda ficam preservados. Edicao, reabertura, devolucao e acoes
locais de entrega/retirada nao substituem as acoes do provedor. O piloto nao
herda beneficios de app, ecommerce ou loja fisica, nao cria cliente a partir do
consumidor de teste e nao dispara emissao fiscal automatica na finalizacao. A
emissao manual continua sujeita as permissoes e regras fiscais da empresa.

Em entrega, a venda conserva `tem_entrega=True`, sem entregador local, e a tela
mostra **Entrega acompanhada pelo iFood**. A dispensa do entregador no finalizador
exige o vinculo DEV valido e permissao de venda na empresa; nao se aplica aos
outros canais. O valor de frete precisa estar explicitamente informado e ser
nao negativo. No online, a responsabilidade pelo frete positivo e a taxa de
servico precisam corresponder as condicoes acima. Frete desconhecido, total
divergente ou outras condicoes nao suportadas continuam bloqueados.

### Roteiro de validacao

1. Use banco e empresa ficticios, credenciais exclusivas do aplicativo de testes
   e a loja de testes correspondente. Nao copie credenciais ou dados de producao.
2. Configure a empresa e a loja do piloto. Mantenha catalogo e Financial
   desligados; o polling deve ficar restrito a empresa e loja autorizadas.
3. No app/site do iFood em modo de teste, monte um pedido contendo somente o
   produto aprovado, uma unidade e as condicoes comerciais acima. O gerador
   automatico do Developer nao permite escolher o SKU e nao serve como prova
   deste ensaio. Para multicategoria, siga a geracao manual oficial.
4. Confira o pedido recebido em **Configuracoes > Integracoes > iFood > Pedidos
   para homologacao** e configure o ID exato antes de importar no PDV.
5. Registre o saldo inicial, reservas e lotes. Use **Enviar ao PDV de teste** e
   confira uma unica reserva; repetir o envio nao pode alterar as contagens.
6. Abra a venda pelo vinculo do painel. Confira canal iFood, item, frete, taxa e
   totais. No offline, registre o dinheiro presencial exato. No online, use
   **Concluir venda e baixar estoque**; nao registre outro pagamento nem abra a
   cobranca manual. Confira a evidencia externa e o repasse ainda a conciliar.
7. Confira uma unica baixa FIFO, reserva encerrada e a venda finalizada. Use
   **Atualizar pedidos** para reler o estado local sem consultar o provedor.
8. Verifique produtos de controle e outra empresa, reenvios, tentativas
   simultaneas, cancelamento e rollback. Nao chame o ensaio local simulado de
   pedido oficial recebido do iFood.

Para uma unidade, o saldo disponivel diminui na reserva; na finalizacao, a
quantidade fisica diminui e a reserva e encerrada, mantendo o mesmo disponivel.
O resultado externo do canal e as cobrancas Financial exigem verificacoes
separadas. Este piloto nao habilita sincronizacao continua nem producao.

Referencia: [geracao de pedidos de teste](https://developer.ifood.com.br/en-US/docs/getting-started/first-steps/generate-test-order).

## Procedimento de homologacao

1. Criar o aplicativo centralizado na categoria Groceries.
2. Manter a escrita de catalogo desligada.
3. Habilitar as operacoes de pedidos somente na janela assistida de teste.
4. Gerar pedidos pela loja de teste do iFood.
5. Comprovar Orders Virtual Bag e o fluxo completo de Picking: iniciar, alterar
   quantidade, remover item, finalizar e consultar novamente a sacola.
6. Desligar o polling ao terminar a sessao, se ainda nao houver go-live.

## Referencias oficiais

- Eventos e polling: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/events/polling-overview>
- Eventos de pedidos: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/events/order-events/>
- Endpoints de pedidos: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/order/endpoints>
- Criterios de homologacao: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/order/homologation/>
- Picking: <https://developer.ifood.com.br/pt-BR/docs/groceries/guides/modules/picking/general>
