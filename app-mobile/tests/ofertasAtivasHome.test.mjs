import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const service = fs.readFileSync(path.join(root, 'src/services/shop.service.ts'), 'utf8');
const home = fs.readFileSync(path.join(root, 'src/screens/HomeScreen.tsx'), 'utf8');

assert.match(service, /\/ecommerce\/ofertas-ativas/);
assert.match(service, /canal:\s*["']app["']/);
assert.match(home, /listarOfertasAtivas/);
assert.match(home, /resizeMode=["']contain["']/);
assert.match(home, /Linking\.openURL\(oferta\.link_path\)/);
assert.match(home, /1 de \{totalPaginas\}/);
assert.match(home, /expand-outline/);
assert.match(home, /oferta\.cta_label/);

console.log('ofertasAtivasHome: ok');
