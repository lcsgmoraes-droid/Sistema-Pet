import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const apiSource = readFileSync(resolve(__dirname, '../src/services/api.ts'), 'utf8');
const shopSource = readFileSync(resolve(__dirname, '../src/services/shop.service.ts'), 'utf8');

assert.match(
  apiSource,
  /'X-Client-Channel': 'app'/,
  'app mobile deve identificar o canal app em todas as chamadas',
);

assert.match(
  apiSource,
  /'X-Canal-Venda': 'app'/,
  'app mobile deve enviar X-Canal-Venda para compatibilidade com o backend',
);

assert.match(
  shopSource,
  /origem: 'app'/,
  'checkout do app deve enviar origem app no payload',
);

console.log('App channel header checks passed.');
