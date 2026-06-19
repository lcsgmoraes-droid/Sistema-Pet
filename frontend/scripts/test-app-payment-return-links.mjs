import assert from "node:assert/strict";
import {
  buildAppPaymentReturnLinks,
  readAppPaymentReturnParams,
} from "../src/utils/appPaymentReturnLinks.js";

const params = readAppPaymentReturnParams(
  "?payment_status=pending&pedido_id=PED-123&loja=atacadao&tenant=ignorado",
);

assert.deepEqual(
  params,
  {
    paymentStatus: "pending",
    pedidoId: "PED-123",
    loja: "atacadao",
  },
  "retorno do app deve preservar status, pedido e loja",
);

assert.deepEqual(
  buildAppPaymentReturnLinks(params),
  {
    deepLink:
      "corepet://app/pedidos?payment_status=pending&pedido_id=PED-123&loja=atacadao",
    androidIntentLink:
      "intent://app/pedidos?payment_status=pending&pedido_id=PED-123&loja=atacadao#Intent;scheme=corepet;package=br.com.corepet.app;end",
    retryLink:
      "corepet://app/pedidos?payment_status=pending&pedido_id=PED-123&loja=atacadao",
  },
  "retorno de compra feita pelo app deve apontar novamente para o app, sem fallback para ecommerce",
);

assert.equal(
  buildAppPaymentReturnLinks(params).retryLink.includes("/app?loja="),
  false,
  "botao de retorno do app nao deve mandar para a entrada web da loja",
);

console.log("App payment return link checks passed.");
