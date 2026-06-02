import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

const sidebarSource = readFileSync(
  resolve(__dirname, '../src/components/pdv/PDVVendasRecentesSidebar.jsx'),
  'utf8',
);

const hookSource = readFileSync(
  resolve(__dirname, '../src/hooks/usePDVVendasRecentes.js'),
  'utf8',
);

assert.match(
  sidebarSource,
  /function isRetiradaOnline/,
  'painel de vendas recentes deve identificar retirada de pedidos online',
);

assert.match(
  sidebarSource,
  /pedido\(s\) online aguardando separacao/,
  'PDV deve exibir aviso chamativo para pedidos online pendentes de separacao',
);

assert.match(
  sidebarSource,
  /marcarProntoRetirada\(e, venda\.id\)/,
  'PDV deve permitir marcar pedido online como pronto para retirada',
);

assert.match(
  sidebarSource,
  /Informar quem retirou/,
  'senha de retirada deve abrir o campo para informar quem retirou',
);

assert.match(
  hookSource,
  /\/vendas\/\$\{vendaId\}\/marcar-pronto-retirada/,
  'hook do PDV deve chamar a rota de marcar retirada pronta',
);

console.log('PDV online order action checks passed.');
