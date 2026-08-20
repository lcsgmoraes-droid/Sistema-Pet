import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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

const viewSource = readFileSync(
  new URL("../src/pages/ecommerce/EcommerceConfigView.jsx", import.meta.url),
  "utf8",
);
const configSource = readFileSync(
  new URL("../src/pages/ecommerce/EcommerceConfig.jsx", import.meta.url),
  "utf8",
);

for (const technicalField of [
  "OAuth Client ID",
  "OAuth Client Secret",
  "Access token",
  "URL do webhook",
  "Configuracao avancada",
]) {
  assert.equal(
    viewSource.includes(technicalField),
    false,
    `tenant nao deve visualizar o campo tecnico: ${technicalField}`,
  );
}

assert.match(
  viewSource,
  /Clique em Conectar para entrar no Mercado Pago e autorizar o CorePet/,
  "tela deve orientar o fluxo de autorizacao em um clique",
);
assert.match(
  viewSource,
  /A conexão está temporariamente indisponível\. Fale com o suporte CorePet\./,
  "falha de configuracao da plataforma nao deve expor credenciais ao tenant",
);
assert.doesNotMatch(
  configSource,
  /oauth_client_(id|secret)\s*:/,
  "frontend nao deve enviar credenciais OAuth do tenant",
);
assert.doesNotMatch(
  configSource,
  /webhook_secret\s*:/,
  "frontend nao deve enviar segredo de webhook do tenant",
);
assert.doesNotMatch(
  configSource,
  /data\.missing|OAuth Mercado Pago ainda nao esta configurado/,
  "mensagens ao tenant nao devem expor configuracao interna do CorePet",
);
assert.doesNotMatch(
  configSource,
  /environment:\s*paymentConfig\.environment/,
  "tenant nao deve escolher o ambiente do gateway",
);

console.log("Mercado Pago OAuth return checks passed.");
