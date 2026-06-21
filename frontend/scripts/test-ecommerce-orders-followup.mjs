import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceOrdersPage.jsx"),
  "utf8",
);
const ordersHookSource = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceOrders.js"),
  "utf8",
);

assert.match(
  source,
  /function OrderPaymentFollowup/,
  "pagina de pedidos deve ter um bloco explicito de acompanhamento de pagamento",
);

assert.match(
  source,
  /onOpenPayment\(order\.payment_url\)/,
  "pedido pendente deve permitir reabrir o link de pagamento salvo",
);

assert.match(
  source,
  /Pagamento aprovado/,
  "pedido aprovado deve explicar ao cliente que a loja ja recebeu a venda",
);

assert.match(
  source,
  /function getOrderFulfillmentStatus/,
  "pagina de pedidos deve traduzir o status operacional da venda",
);

assert.match(
  source,
  /Pronto para retirada/,
  "pedido pronto deve informar claramente que ja pode ser retirado",
);

assert.match(
  source,
  /A retirar/,
  "pedido online pendente de retirada deve aparecer como a retirar para o cliente",
);

assert.match(
  source,
  /Compra com entrega/,
  "pedido com entrega deve aparecer como compra com entrega sem pedir retirada",
);

assert.match(source, /Pedido retirado por/, "historico deve mostrar quem retirou o pedido");

assert.match(
  ordersHookSource,
  /hasOpenFulfillmentOrder/,
  "tela de pedidos deve atualizar automaticamente retiradas em aberto",
);

assert.match(
  source,
  /aprovado:\s*["']#10b981["']/,
  "status aprovado deve ter cor positiva propria",
);

assert.match(
  source,
  /function getOrderChannelLabel/,
  "pagina de pedidos deve traduzir canal do pedido",
);

assert.match(
  source,
  /order\.canal_label/,
  "pagina de pedidos deve priorizar canal_label vindo da API",
);

assert.match(source, /App mobile/, "pagina de pedidos deve exibir canal app mobile de forma clara");

assert.match(
  source,
  /Loja fisica \/ ERP/,
  "pagina de pedidos deve exibir canal loja fisica/ERP de forma clara",
);

console.log("E-commerce orders follow-up checks passed.");
