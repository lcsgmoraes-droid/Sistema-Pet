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

**Financial e relatorios gerais em DEV:** a ligacao por pedido ja aplica a revisao
Financial ativa sobre a base historica, pela ponte exata do PDV ou por vinculo
manual explicitamente confirmado. Comissao e taxa de pagamento sao componentes
separados, com nome e valor; somente o que faltar continua pendente. Zero exige
evento explicito. Chegada tardia e revisao atualizam a leitura sem acumular taxas,
refazer CMV ou movimentar caixa, reserva e estoque. Relatorio, DRE, ponto de
equilibrio, dashboard, rankings/IA e exportacoes preservam valores desconhecidos
como pendentes. A confirmacao bancaria do repasse continua separada.

O pedido oficial #1420 ainda nao tem Financial proprio fornecido pelo iFood. A
ligacao foi ensaiada com massa `synthetic`, identificada como simulacao DEV e
restaurada ao final; ela nunca liberou lucro real. O aceite local nao conclui a
homologacao Financial oficial, nao habilita leitura externa em producao e nao
amplia automaticamente o piloto. Detalhes e limites: [Financial em DEV](IFOOD_FINANCIAL_DEV.md).

Ao finalizar a venda no PDV, o fluxo normal faz a baixa FIFO dos lotes e encerra
a reserva na mesma transacao. Repeticoes e concorrencia nao podem executar outra
baixa. Cancelar a venda antes da finalizacao somente libera a reserva, sem
inventar uma entrada de estoque. O cancelamento remoto impede a finalizacao
depois de seu evento ser recebido e registrado no CorePet. Neste piloto, a
liberacao local exige a acao explicita **Cancelar** no PDV. Nao ha estorno
retroativo automatico por eventos do provedor.

O cancelamento local depois da baixa exige venda finalizada, ponte `sold`,
reserva original, unico item e comprovante da saida compativeis. A transacao
recompoe a unidade nos lotes originais e usa o CMV da prova, preservando o JSON
original; nao executa outro FIFO nem usa o custo atual do produto. Lote bloqueado
ou vencido conserva sua restricao. Prova adulterada, saida inconsistente, retorno
anterior ou efeito financeiro local inesperado bloqueiam a operacao, sem retorno
parcial de estoque. Concorrencia e repeticao nao podem criar segunda entrada.

`pdv_bridge` apresenta `stock_restored` e `cancellation`. Antes da baixa,
`stock_restored=false` significa reserva liberada sem entrada; depois da baixa,
`stock_restored=true` comprova a recomposicao validada. A evidencia acrescenta
`scope=local_dev`, `provider_cancellation_confirmed=false` e, no online,
`refund_status=pending_provider_review`, com `refunded_amount=null`. A ponte fica
`cancelled`; o recebivel de evidencia passa a `cancelled_pending_provider_review`.
O registro local do pagamento e preservado com status `cancelado` para exclusao
dos saldos ativos. A prova original da aprovacao externa permanece auditavel.

Nenhuma dessas acoes envia `CAN` ao iFood ou devolve dinheiro ao consumidor.
A interface informa **Cancelado no CorePet**, **Lotes originais recompostos** ou
**Reserva liberada, sem entrada fisica**, e **Estorno iFood a conferir** no online.
Cancelamento remoto, reembolso e cobrancas Financial exigem comprovacao propria;
`null` nao significa reembolso zero ou concluido.

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
9. Preserve o pedido oficial #1420. Para cancelamento, use pedidos ficticios
   separados do mesmo SKU: um ainda reservado e outro ja finalizado. Confira
   liberacao sem entrada no primeiro e recomposicao dos lotes/CMV originais no
   segundo. Repita a chave idempotente e os eventos recebidos, confirmando que
   nao houve outra baixa, reserva ou entrada. Confira o pagamento auditado e a
   ausencia de reembolso ficticio em caixa ou banco.

### Situacao dos testes de cancelamento

A ampliacao possui **303 testes unitarios backend**, **37 cenarios PostgreSQL**
e **320 testes frontend iFood/produto** aprovados em validacoes focadas. Os testes
de banco cobrem cancelamento depois da baixa, lotes/CMV originais, repeticao,
concorrencia e rollback. Esses totais nao substituem o gate completo do commit final.

No runtime DEV, o cancelamento antes da baixa passou com outro pedido sintetico:
o SKU `018631.1` voltou a fisico **29**, reservado **3**, disponivel **26**, sem
entrada fisica. Evento `CAN` repetido e a mesma chave de solicitacao retornaram
o resultado ja registrado (HTTP 200); uma nova solicitacao apos o cancelamento
foi recusada (HTTP 400), sem duplicar movimentos. O pedido #1420 foi preservado.
O cancelamento depois da baixa tambem passou: fisico 29 para 28 na saida e de
volta a 29 na entrada, lotes originais recompostos e CMV **R$ 43,94** nas duas
movimentacoes. Repeticoes nao geraram outra entrada. A interface mostrou
**Cancelado no CorePet**, **Lotes originais recompostos** e **Estorno iFood a conferir**.
As linhas anteriores, incluindo o pedido #1420, e os hashes das 12 tabelas
financeiras de controle permaneceram iguais. A configuracao privada foi restaurada;
os dois pedidos sinteticos cancelados ficaram no historico. Prova local fora do
Git: `cancel-pilot-final-proof.json`. Gate completo e CI do head final devem ser
conferidos no PR #1561 antes de qualquer merge ou publicacao autorizados.

O vinculo de um produto ja publicado continua sendo outra etapa: escolher outro
EAN conferido no catalogo da mesma loja, sem reutilizar o SKU criado no primeiro
teste nem criar um anuncio duplicado. Essa ampliacao de cancelamento nao o executa.

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
