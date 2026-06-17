import assert from "node:assert/strict";
import { readMercadoPagoOAuthReturn } from "../src/utils/mercadoPagoOAuthReturn.js";

assert.deepEqual(
  readMercadoPagoOAuthReturn("?mercadopago_oauth=connected"),
  {
    status: "success",
    message: "Mercado Pago conectado com sucesso.",
  },
  "callback conectado deve virar uma mensagem positiva",
);

assert.deepEqual(
  readMercadoPagoOAuthReturn("?mercadopago_oauth=error&mercadopago_message=Falha%20OAuth"),
  {
    status: "error",
    message: "Falha OAuth",
  },
  "callback com erro deve preservar a mensagem enviada pelo backend",
);

assert.equal(
  readMercadoPagoOAuthReturn("?foo=bar"),
  null,
  "paginas sem retorno OAuth nao devem mostrar alerta contextual",
);

console.log("Mercado Pago OAuth return checks passed.");
