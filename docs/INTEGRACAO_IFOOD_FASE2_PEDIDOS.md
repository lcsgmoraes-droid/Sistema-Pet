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
3. Consulta e armazenamento do pedido completo ao receber `PLACED`.
4. Atualizacao local dos estados `CONFIRMED`, `SEPARATION_STARTED`,
   `READY_TO_PICKUP`, `DISPATCHED`, `CONCLUDED` e `CANCELLED`.
5. Confirmacao do pedido.
6. Inicio da preparacao/separacao.
7. Aviso de pedido pronto.
8. Despacho somente para `DELIVERY` com `deliveredBy=MERCHANT`.
9. Consulta dinamica dos motivos de cancelamento e envio do motivo escolhido.
10. Validacao de codigo de coleta e de entrega.

A tela mostra itens, pagamento, bandeira/troco, cupons e seus responsaveis,
endereco e localizador do telefone para servir como evidencia da homologacao.

## Travas operacionais

As tres operacoes externas sao independentes:

- `IFOOD_CATALOG_WRITE_ENABLED=false`: bloqueia qualquer envio de produto.
- `IFOOD_ORDER_OPERATIONS_ENABLED=false`: bloqueia ACK e acoes de pedido.
- `IFOOD_ORDER_POLLING_ENABLED=false`: impede o polling automatico.

O polling automatico so inicia quando as duas travas de pedidos estao ativas.
O intervalo minimo e 30 segundos e apenas um worker lider executa o ciclo.

## Procedimento de homologacao

1. Criar o aplicativo centralizado na categoria Groceries.
2. Manter a escrita de catalogo desligada.
3. Habilitar as operacoes de pedidos somente na janela assistida de teste.
4. Gerar pedidos pela loja de teste do iFood.
5. Comprovar recebimento, confirmacao, cancelamento, despacho e validacao.
6. Desligar o polling ao terminar a sessao, se ainda nao houver go-live.

## Referencias oficiais

- Eventos e polling: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/events/polling-overview>
- Eventos de pedidos: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/events/order-events/>
- Endpoints de pedidos: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/order/endpoints>
- Criterios de homologacao: <https://developer.ifood.com.br/pt-BR/docs/guides/modules/order/homologation/>
