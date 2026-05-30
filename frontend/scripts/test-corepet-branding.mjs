import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { cwd } from 'node:process';
import assert from 'node:assert/strict';

const root = cwd();
const read = (path) => readFileSync(join(root, path), 'utf8');
const readRepo = (path) => readFileSync(join(root, '..', path), 'utf8');

const indexHtml = read('index.html');
const login = read('src/pages/Login.jsx');
const layout = read('src/components/Layout.jsx');
const favicon = read('public/favicon.svg');

assert.match(indexHtml, /<title>CorePet - Sistema de Gestao Integrada<\/title>/);
assert.match(indexHtml, /content="CorePet centraliza a gestao do petshop/);
assert.match(favicon, /CorePet favicon/);

assert.match(login, /\/brand\/corepet\/corepet-horizontal\.png/);
assert.doesNotMatch(login, /Pet Shop Pro/);
assert.match(login, /Gestao integrada para petshops/);

assert.match(layout, /\/brand\/corepet\/corepet-horizontal\.png/);
assert.match(layout, /\/brand\/corepet\/corepet-icon-64\.png/);
assert.doesNotMatch(layout, /Pet Shop Pro/);

for (const path of [
  'src/pages/Ajuda.jsx',
  'src/pages/AppPublicEntry.jsx',
  'src/components/ModuloBloqueado.jsx',
  'src/pages/MeuPlano.jsx',
  'src/pages/LegalPage.jsx',
  'src/pages/LandingPage.jsx',
  'src/pages/Planos.jsx',
  'src/pages/Register.jsx',
  'src/pages/entregas/RastreioPublico.jsx',
]) {
  const content = read(path);
  assert.doesNotMatch(content, /Pet Shop Pro|Sistema Pet/, `${path} should use CorePet in public copy`);
}

assert.doesNotMatch(
  readRepo('backend/app/routes/ecommerce_auth.py'),
  /Pet Shop Pro/,
  'ecommerce auth e-mails should use CorePet in subjects and body text',
);

for (const asset of [
  'public/brand/corepet/corepet-horizontal.png',
  'public/brand/corepet/corepet-symbol.png',
  'public/brand/corepet/corepet-icon-32.png',
  'public/brand/corepet/corepet-icon-64.png',
  'public/brand/corepet/corepet-icon-192.png',
  'public/brand/corepet/corepet-icon-512.png',
]) {
  assert.ok(existsSync(join(root, asset)), `${asset} should exist`);
}

console.log('CorePet branding checks passed.');
