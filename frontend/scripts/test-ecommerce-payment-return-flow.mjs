import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const ordersHookSource = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceOrders.js"),
  "utf8",
);
const ecommerceMvpSource = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceMVP.jsx"),
  "utf8",
);

assert.match(
  ordersHookSource,
  /import\s+\{\s*useCallback,\s*useEffect,\s*useRef,\s*useState\s*\}\s+from\s+["']react["']/,
  "hook de pedidos deve usar callbacks estaveis e trava de carregamento",
);

assert.match(
  ordersHookSource,
  /const\s+loadingOrdersRef\s*=\s*useRef\(false\)/,
  "carregamento de pedidos deve ter trava contra requisicoes concorrentes",
);

assert.match(
  ordersHookSource,
  /const\s+loadOrdersDetailed\s*=\s*useCallback\(async\s*\(\)\s*=>/,
  "loadOrdersDetailed deve ser estavel para nao reativar efeitos do retorno de pagamento",
);

assert.match(
  ordersHookSource,
  /if\s*\(\s*loadingOrdersRef\.current\s*\)\s*return/,
  "loadOrdersDetailed deve ignorar nova chamada enquanto outra ainda esta em andamento",
);

assert.match(
  ordersHookSource,
  /const\s+recordOrderId\s*=\s*useCallback\(\s*async\s*\(orderId\)\s*=>/,
  "recordOrderId deve ser estavel para nao repetir o tratamento da URL do Mercado Pago",
);

assert.match(
  ecommerceMvpSource,
  /const\s+handledPaymentReturnSearchRef\s*=\s*useRef\(["']["']\)/,
  "pagina do ecommerce deve lembrar a ultima URL de retorno de pagamento tratada",
);

assert.match(
  ecommerceMvpSource,
  /if\s*\(\s*handledPaymentReturnSearchRef\.current\s*===\s*location\.search\s*\)\s*return/,
  "mesma URL de retorno do Mercado Pago deve ser processada uma unica vez",
);

assert.match(
  ecommerceMvpSource,
  /handledPaymentReturnSearchRef\.current\s*=\s*location\.search/,
  "URL de retorno deve ser marcada como tratada antes de mudar estados da tela",
);

console.log("E-commerce payment return flow checks passed.");
