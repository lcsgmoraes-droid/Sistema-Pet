# Historico de Compras do Cliente por Canal e Notificacoes

## Objetivo

Exibir para o cliente, no ecommerce e no app mobile, todo o historico de compras vinculado ao seu cadastro seguro da loja. O vinculo de identidade desta primeira fatia sera apenas `Cliente.user_id == User.id`, sem conciliacao por email, CPF ou telefone.

Tambem sera incluida notificacao push no app mobile quando uma compra for criada e quando o status do pedido/venda mudar.

## Escopo

- Mostrar pedidos pendentes do checkout ecommerce/app.
- Mostrar vendas confirmadas do ERP/PDV/ecommerce/app associadas ao cliente por `Cliente.user_id`.
- Exibir canal de forma clara, sem rotulo generico "online".
- Reaproveitar a API consumida pelo ecommerce e pelo app mobile sempre que possivel.
- Enviar push para o app mobile quando houver token registrado no `User.push_token`.
- Notificar a compra quando o pedido for criado/finalizado no checkout.
- Notificar atualizacoes vindas do webhook de pagamento.
- Notificar atualizacoes operacionais do pedido, como separacao, pronto para retirada, saiu para entrega e entregue.

## Fora de Escopo Nesta Fatia

- Conciliar historico antigo por email, CPF, telefone ou nome.
- Criar inbox persistente de notificacoes dentro do app.
- Mudar regras de checkout, cobranca ou aprovacao do Mercado Pago. O pagamento continua como esta; esta fatia apenas usa os webhooks de pagamento como gatilho de notificacao e atualizacao visual.

## Regras de Canal

A API retornara o canal bruto e o label pronto para exibicao:

| `canal` | `canal_label` |
| --- | --- |
| `ecommerce` | `Ecommerce` |
| `app` | `App mobile` |
| `loja_fisica` | `Loja fisica / ERP` |
| `mercado_livre` | `Mercado Livre` |
| `shopee` | `Shopee` |
| `amazon` | `Amazon` |

Compras feitas no app mobile devem aparecer como `app`, mesmo usando o mesmo checkout do ecommerce por baixo. Compras feitas no site devem aparecer como `ecommerce`. Vendas registradas diretamente no ERP/PDV devem aparecer como `loja_fisica`.

## Arquitetura

A rota existente `GET /api/checkout/pedidos` sera mantida como contrato principal para ecommerce e app mobile. Ela passara a montar uma lista unificada com duas fontes:

1. `pedidos`: pedidos de checkout ecommerce/app do usuario logado ainda nao consolidados, principalmente `pendente`, `recusado` ou `cancelado`.
2. `vendas`: vendas do cliente ERP vinculado ao usuario logado por `Cliente.user_id == User.id`.

A resposta sera um read model de historico do cliente. Ela nao altera a fonte da verdade: `pedidos` continua sendo a fonte para checkout antes da confirmacao, e `vendas` continua sendo a fonte para vendas consolidadas e historico ERP.

## Modelo de Resposta

Cada item do historico tera estes campos principais:

```json
{
  "historico_id": "venda:123",
  "origem_tipo": "venda",
  "pedido_id": "PED-ABC",
  "venda_id": 123,
  "numero": "VEN-20260620-0001",
  "status": "finalizada",
  "status_entrega": "pronto",
  "canal": "app",
  "canal_label": "App mobile",
  "total": 89.9,
  "created_at": "2026-06-20T16:00:00",
  "itens": [
    {
      "produto_id": 10,
      "nome": "Racao 10kg",
      "quantidade": 1,
      "preco_unitario": 89.9,
      "subtotal": 89.9
    }
  ]
}
```

Para pedidos ainda pendentes sem venda:

```json
{
  "historico_id": "pedido:PED-ABC",
  "origem_tipo": "pedido_online",
  "pedido_id": "PED-ABC",
  "venda_id": null,
  "status": "pendente",
  "canal": "ecommerce",
  "canal_label": "Ecommerce"
}
```

## Deduplicacao

Quando uma venda ja tiver sido gerada a partir de um pedido de checkout ecommerce/app, o historico deve mostrar apenas uma entrada consolidada. A preferencia sera:

1. Se existe `Venda` relacionada ao `Pedido`, mostrar a entrada da venda.
2. Preservar `pedido_id`, `payment_url`, `tipo_retirada`, `palavra_chave_retirada` e dados de drive quando existirem.
3. Nao duplicar o mesmo pedido como `pedido_online` e `venda`. `pedido_online` e apenas um identificador tecnico da API; o cliente continuara vendo o canal explicito em `canal_label`.

O vinculo existente por `IdempotencyKey` de integracao ecommerce-venda e/ou `Venda.observacoes` com o `pedido_id` podera ser usado para associar venda e pedido sem criar uma migracao nesta fatia.

## Fluxo de Dados

### Ecommerce

1. Cliente acessa "Meus Pedidos".
2. Frontend chama `GET /api/checkout/pedidos`.
3. API retorna historico unificado com `canal_label`.
4. Tela exibe canal em cada card e mantem acoes de pagamento pendente, retirada, drive e atualizar status.

### App Mobile

1. Cliente abre "Pedidos".
2. App chama a mesma API `GET /checkout/pedidos`.
3. App exibe o mesmo historico com canal explicito.
4. Ao tocar em push de pedido/status, app navega para a aba "Pedidos".

### ERP/PDV

1. Venda criada/finalizada no ERP fica em `vendas` com `cliente_id`.
2. Se o `Cliente` tem `user_id` igual ao usuario do app/ecommerce, essa venda entra no historico do cliente.
3. Alteracoes de `status_entrega` tambem podem gerar push para o usuario vinculado.

## Notificacoes Push

Sera criado um servico backend pequeno para notificar eventos de pedido ao usuario cliente conforme eles acontecem:

- Compra criada/checkout finalizado: "Pedido recebido" ou "Aguardando pagamento".
- Webhook de pagamento aprovado: "Pagamento aprovado".
- Webhook de pagamento pendente/em analise: "Pagamento em analise".
- Webhook de pagamento recusado/cancelado: "Pagamento nao concluido".
- Separacao/retirada no ERP: "Pedido em separacao" e "Pronto para retirada".
- Entrega/rota no ERP/app entregador: "Pedido saiu para entrega" e "Pedido entregue".

O servico deve:

- Buscar `User.push_token`.
- Ignorar silenciosamente quando nao houver token.
- Enviar via Expo Push API.
- Nao impedir checkout, webhook ou atualizacao de venda se o push falhar.
- Enviar `data` com `source: "order"`, `kind: "order_status"`, `pedido_id`, `venda_id` e `canal`.

O app mobile deve aceitar `source: "order"` e navegar para `Pedidos`.

## Pontos de Integracao

- `backend/app/routes/ecommerce_checkout.py`
  - Ampliar `listar_pedidos_cliente`.
  - Disparar push apos checkout pendente, sem bloquear a resposta.
- `backend/app/routes/ecommerce_webhooks.py`
  - Disparar push quando o status do pedido mudar por webhook de pagamento.
- `backend/app/vendas_routes.py`
  - Disparar push quando `marcar-pronto-retirada`, `marcar-entregue` e atualizacoes relevantes alterarem status.
- `app-mobile/src/screens/orders/OrdersScreen.tsx`
  - Mostrar canal claro no card.
- `app-mobile/src/hooks/usePushNotifications.ts`
  - Navegar para pedidos quando `data.source === "order"`.
- `frontend/src/pages/ecommerce/EcommerceOrdersPage.jsx`
  - Mostrar canal claro no card.

## Tratamento de Erros

- Se nao existir `Cliente` vinculado ao `User`, a API retorna somente pedidos da tabela `pedidos`.
- Falha ao resolver venda relacionada nao deve derrubar a listagem; o pedido aparece como item de checkout.
- Falha no push deve ser logada e ignorada.
- A listagem deve continuar paginada por `limit` e ordenada por data mais recente.

## Testes

Backend:

- Testar que `/checkout/pedidos` retorna pedidos de checkout pendentes do usuario.
- Testar que retorna vendas vinculadas por `Cliente.user_id`.
- Testar que nao retorna vendas de cliente sem vinculo com o usuario.
- Testar que canal `app`, `ecommerce` e `loja_fisica` geram labels corretos.
- Testar que venda consolidada deduplica o pedido de checkout original.
- Testar que a notificacao push deve ser chamada nos eventos de checkout, webhook de pagamento e status operacional sem bloquear erro.

Frontend web:

- Teste fonte/contrato garantindo exibicao de `canal_label`.
- Teste garantindo que botao de pagamento pendente continua existindo.

App mobile:

- Teste fonte/contrato garantindo exibicao de `canal_label`.
- Teste garantindo navegacao para `Pedidos` ao tocar push `source: "order"`.

## Criterios de Aceite

- Cliente ve, no ecommerce e no app, compras feitas por ecommerce, app mobile e loja fisica/ERP quando todas estiverem ligadas por `Cliente.user_id`.
- Cada compra mostra canal claro e nao generico.
- Pedido pendente aparece apos checkout.
- Apos confirmacao, a entrada fica consolidada com a venda quando disponivel.
- App recebe push de compra/status quando o usuario tem `push_token`.
- Falha de push nao quebra checkout, webhook nem atualizacao de venda.
