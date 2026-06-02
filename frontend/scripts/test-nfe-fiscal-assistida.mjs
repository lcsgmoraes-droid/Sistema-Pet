import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(
  resolve(__dirname, '../src/utils/nfeFiscalAssistida.js'),
  'utf8',
);

assert.match(
  source,
  /A nota ainda nao foi criada/,
  'assistente fiscal deve avisar que a nota nao foi criada quando houver pendencia',
);

assert.match(
  source,
  /Autorizar correcao fiscal e emitir a nota agora\?/,
  'assistente fiscal deve pedir autorizacao clara antes de aplicar sugestoes fiscais',
);

console.log('NFe fiscal assistant checks passed.');
