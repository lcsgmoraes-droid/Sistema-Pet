import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(
  resolve(__dirname, '../src/pages/ecommerce/EcommerceOrdersPage.jsx'),
  'utf8',
);

assert.match(
  source,
  /function OrderPaymentFollowup/,
  'pagina de pedidos deve ter um bloco explicito de acompanhamento de pagamento',
);

assert.match(
  source,
  /onOpenPayment\(order\.payment_url\)/,
  'pedido pendente deve permitir reabrir o link de pagamento salvo',
);

assert.match(
  source,
  /Pagamento aprovado/,
  'pedido aprovado deve explicar ao cliente que a loja ja recebeu a venda',
);

assert.match(
  source,
  /aprovado:\s*'#10b981'/,
  'status aprovado deve ter cor positiva propria',
);

console.log('E-commerce orders follow-up checks passed.');
