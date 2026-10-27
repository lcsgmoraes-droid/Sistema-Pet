# Pedidos Amazon e NF-e CorePet — contrato v1

O EcommerceAI importa os fatos do pedido e coordena a fila. O CorePet resolve
produto e tributacao, emite NF-e 55 e guarda o XML autorizado. O EcommerceAI
envia os mesmos bytes a Amazon quando o aplicativo tiver permissao. Esta trilha
fiscal nao cria outra Venda, recebimento, conta ou movimento de estoque.

## Identidade e consentimento

- Reutilizar a conexao CorePet/EcommerceAI por Bearer opaco; tenant vem do token.
- Escopos novos e separados: `fiscal:prepare`, `fiscal:issue`, `fiscal:read`.
  Conexoes antigas nao recebem esses poderes automaticamente.
- Um operador configura `(tenant, channel=amazon, seller_id)`, confere o CNPJ do
  emitente e vincula cada SKU ao produto/kit CorePet. Nunca resolver por titulo.
- Emissao automatica comeca desativada; ativacao humana registra data e politica
  de descontos. Pedido anterior a ativacao exige vinculo com nota existente ou
  revisao explicita, nunca uma nova emissao automatica.
- Identidade permanente do pedido: `(tenant_id, channel, seller_id,
  external_order_id)`, inclusive depois de reconectar a integracao.

## API de maquina CorePet

Prefixo: `/integracoes/ecommerceai/fiscal`.

- `POST /orders`: preparar/upsert; exige `fiscal:prepare`.
- `GET /orders/{id}`: consultar estado local; exige `fiscal:read`.
- `POST /orders/{id}/emitir`: emitir a revisao esperada; exige `fiscal:issue` e
  configuracao da conta. Corpo: `expected_revision`, `expected_payload_hash`.
- `POST /orders/{id}/consultar`: reconciliar com o emissor; exige `fiscal:read`.
- `GET /orders/{id}/xml` e `/danfe`: documento autorizado; `fiscal:read`.

O upsert retorna o mesmo ID para a mesma identidade. Mesma revisao com conteudo
diferente ou revisao antiga retorna 409. Revisao posterior so muda rascunho ainda
nao enviado. O snapshot e congelado antes de qualquer chamada de emissao.

Exemplo sintetico (valores monetarios como strings decimais):

```json
{
  "schema_version": "1.0",
  "channel": "amazon",
  "seller_id": "SELLER_EXEMPLO",
  "marketplace_id": "A2Q3Y263D00KWC",
  "external_order_id": "701-0000000-0000000",
  "source_revision": 1,
  "order_status": "Unshipped",
  "purchased_at": "2026-10-27T12:00:00Z",
  "source_updated_at": "2026-10-27T12:01:00Z",
  "emitter_cnpj": "11222333000181",
  "recipient": {
    "name": "Cliente de teste",
    "document": "12345678909",
    "ie_status": "9",
    "address": {
      "street": "Rua de teste",
      "number": "10",
      "complement": null,
      "district": "Centro",
      "city": "Sao Paulo",
      "municipality_code": "3550308",
      "state": "SP",
      "postal_code": "01001000"
    }
  },
  "items": [{
    "external_item_id": "ITEM_TESTE",
    "seller_sku": "KIT_TESTE_2",
    "asin": "ASIN_TESTE",
    "quantity": "1",
    "unit_price": "100.00",
    "gross_amount": "100.00",
    "discount_amount": "0.00"
  }],
  "totals": {
    "currency": "BRL",
    "products": "100.00",
    "discount": "0.00",
    "freight": "0.00",
    "invoice_total": "100.00"
  },
  "payments": [{"fiscal_method": "03", "amount": "100.00", "integration_type": "2"}],
  "buyer_paid_total": "100.00",
  "source_evidence": {"tax": "available", "recipient": "available", "payment": "available"}
}
```

Nao aceitar NCM, CFOP, CSOSN, regime, serie, ambiente ou numero do EcommerceAI.
Esses dados sao resolvidos pelo CorePet. Validar DV do CPF/CNPJ, endereco BR,
CEP/UF/IBGE coerentes, quantidades e centavos; dados mascarados e metodo de
pagamento desconhecido bloqueiam. CEP pode completar apenas geografia coerente
com cidade/UF de origem; nunca inventar numero, documento ou produto.

Politicas da conta:

- `source_discounts`: usar apenas descontos de origem explicitos (padrao).
- `buyer_payment_total`: escolha humana explicita para esta loja; ratear a
  diferenca positiva entre valor comercial e pagamento documentado como desconto
  adicional, preservando centavos e registrando ambos os valores e a politica.

Sem essa escolha, diferenca entre pagamento e total e um bloqueio, nao desconto
inferido. Identificador de promocao nao comprova valor ou financiamento.

Resposta de preparacao/consulta:

```json
{
  "id": 1,
  "channel": "amazon",
  "seller_id": "SELLER_EXEMPLO",
  "external_order_id": "701-0000000-0000000",
  "source_revision": 1,
  "payload_hash": "sha256_do_snapshot_fiscal",
  "status": "ready",
  "blockers": [],
  "totals": {"currency": "BRL", "products": "100.00", "discount": "0.00", "freight": "0.00", "invoice_total": "100.00"},
  "numero": null,
  "chave": null,
  "protocolo": null,
  "xml_available": false,
  "danfe_available": false
}
```

Estados: `blocked`, `ready`, `processing`, `unknown`, `authorized`, `rejected`,
`canceled`. Bloqueios tem `code`, `message` e `field` opcional. Rotas humanas de
gestao ficam em `/manage/accounts`, `/manage/mappings`, `/manage/orders`; usam
autenticacao e tenant do operador, nao o token de maquina.

`totals` representa os valores fiscais finais, incluindo a politica de desconto
aprovada, com moeda e centavos como strings. O EcommerceAI preserva
`source_updated_at` quando os fatos comerciais nao mudaram, mantendo o mesmo
corpo para a mesma revisao.

## Fila e recuperacao

O EcommerceAI persiste o trabalho fiscal por usuario/conta/pedido antes da rede,
com revisao, hash e lease. Importacao de pedido Unshipped/PartiallyShipped
alimenta a fila; backstop agendado recupera trabalhos. Nao esperar etiqueta,
package ou `ORDER_CHANGE.processed`, pois o agendamento DBA depende da NF.

O CorePet persiste chave idempotente, payload e estado antes do POST IntNFe.
Resposta incerta consulta o mesmo documento; nunca cria outra nota. Nao renovar
automaticamente a chave depois da janela de idempotencia do emissor. Concorrencia
e unicidade devem ser asseguradas no banco, nao apenas em memoria.

XML so e entregue/uploadado apos assinatura/digest, CNPJ, chave, protocolo,
destinatario, valores e referencia do pedido conferidos. Preservar os bytes do
XML autorizado e nunca reserializar para upload. Tratar rejeicao, cancelamento e
status desconhecido de forma explicita.

## Amazon

Orders v2026: `GET /orders/2026-01-01/orders/{id}` com
`BUYER,RECIPIENT,TAX,PAYMENT,PROCEEDS,PROMOTION,FULFILLMENT`. CPF/CNPJ vem de
`tax.taxRegistrations[]` com entidade BUYER, nao de MERCHANT. HTTP 200 com PII
ausente/mascarada nao significa pronto para emitir. Nao precisa de RDT nessa
versao, mas precisa das permissoes restritas apropriadas.

Upload e consulta exigem Tax Invoicing (Restricted) e Restricted Availability no
Brasil. Configuracao deve permitir fallback com XML disponivel para download.

- POST `/delivery/2022-07-01/invoice?orderId=...`.
- Corpo: `invoiceContent=Base64(xml)`,
  `contentMD5Value=Base64(MD5_digest(xml))`, `invoiceType=Outbound`,
  `programType=EasyShip` ou `SelfShip`, conforme a modalidade comprovada do
  pedido merchant, marketplace BR. Usar exatamente os mesmos bytes.
- GET `/delivery/2022-07-01/invoice/status` por `invoiceId=chave44` e parametros
  obrigatorios. Conferir chave e pedido. HTTP 200 do POST e apenas envio.
- Processing/NotFound/Errored/Rejected/PartiallyAccepted nao sao aceite integral.
  Consultar exclusivamente pela chave esperada e exigir `amazonOrderId` exato.
  `invoiceStatus=Accepted` e necessario; quando `orderInvoicingStatus` ou
  `invoices` estiverem presentes, todos os estados relevantes devem confirmar
  aceite, incluindo a entrada da chave exata. Uma lista presente sem a chave
  esperada nunca comprova aceite. Suportar tambem a resposta legada sem esses
  dois campos opcionais.
  Timeout exige consulta antes de reenviar; nao usar retries cegos do gateway
  para POST. Persistir hash/chave e repetir apenas os mesmos bytes quando seguro.
- 403/capacidade ausente bloqueia somente upload; a NF e o XML continuam visiveis.

Fontes: [PII Orders](https://developer-docs.amazon.com/sp-api/docs/access-orders-pii),
[upload](https://developer-docs.amazon.com/sp-api/docs/submit-an-invoice-delivery-by-amazon-order),
[consulta](https://developer-docs.amazon.com/sp-api/docs/check-the-invoice-status-for-a-delivery-by-amazon-order).
Modelo oficial: [Delivery Shipment Invoicing](https://github.com/amzn/selling-partner-api-models/blob/main/models/delivery-by-amazon/deliveryShipmentInvoiceV2022-07-01.json).

## Validacao e ativacao

Fixtures ficticias, emissor e Amazon simulados em DEV. Cobrir isolamento,
reconexao, duas execucoes concorrentes, timeout, snapshot alterado, dados
ausentes, pagamentos, kits, XML adulterado e aceite parcial. Nenhuma nota real
sera emitida por testes. Publicacao e ativacao em producao dependem de
autorizacao explicita, apos a demonstracao e os testes.
