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
const legalPage = read('src/pages/LegalPage.jsx');
const blingIntegracao = read('src/pages/configuracoes/BlingIntegracao.jsx');
const favicon = read('public/favicon.svg');
const robots = read('public/robots.txt');
const sitemap = read('public/sitemap.xml');

assert.match(indexHtml, /<title>CorePet - Sistema de Gestao Integrada<\/title>/);
assert.match(indexHtml, /content="CorePet centraliza a gestao do petshop/);
assert.match(favicon, /CorePet favicon/);
assert.match(robots, /https:\/\/corepet\.com\.br\/sitemap\.xml/);
assert.doesNotMatch(robots, /mlprohub\.com\.br/);
assert.match(sitemap, /https:\/\/corepet\.com\.br\/landing/);
assert.match(sitemap, /https:\/\/corepet\.com\.br\/login/);
assert.match(sitemap, /https:\/\/corepet\.com\.br\/register/);
assert.doesNotMatch(sitemap, /mlprohub\.com\.br/);

assert.match(login, /\/brand\/corepet\/corepet-horizontal\.png/);
assert.doesNotMatch(login, /Pet Shop Pro/);
assert.match(login, /Gestao integrada para petshops/);

assert.match(layout, /\/brand\/corepet\/corepet-horizontal\.png/);
assert.match(layout, /\/brand\/corepet\/corepet-icon-64\.png/);
assert.doesNotMatch(layout, /Pet Shop Pro/);

assert.match(legalPage, /atacadaopetpp@gmail\.com/);
assert.doesNotMatch(legalPage, /admin@mlprohub\.com\.br/);
assert.doesNotMatch(blingIntegracao, /Sistema Pet/);
assert.match(blingIntegracao, /CorePet/);

const legacyBrandPattern = /Pet Shop Pro|Sistema Pet|MLProHub|PetShop ERP/;

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
  assert.doesNotMatch(content, legacyBrandPattern, `${path} should use CorePet in public copy`);
}

for (const path of [
  'src/components/OpsLayout.jsx',
]) {
  const content = read(path);
  assert.doesNotMatch(content, legacyBrandPattern, `${path} should use CorePet in runtime copy`);
}

for (const path of [
  'backend/app/auth_routes_multitenant.py',
  'backend/app/services/email_service.py',
  'backend/app/services/ops_alert_notifier.py',
  'backend/app/health_router.py',
  'backend/app/routers/whatsapp_config.py',
  'backend/app/campaigns/notification_sender.py',
  'backend/app/bling_integration.py',
  'backend/app/services/bling_sync_service.py',
  'backend/app/bling_sync_routes.py',
  'backend/app/veterinario_calendar.py',
  'backend/app/config.py',
  'backend/app/main.py',
]) {
  const content = readRepo(path);
  assert.doesNotMatch(content, legacyBrandPattern, `${path} should use CorePet in runtime copy`);
}

for (const path of [
  '.env.example',
  'backend/.env.example',
]) {
  const content = readRepo(path);
  assert.match(content, /SYSTEM_NAME=CorePet ERP/, `${path} should document CorePet as the app name`);
  assert.doesNotMatch(content, /Pet Shop Pro|PetShop ERP/, `${path} should not expose old product branding`);
}

assert.match(
  readRepo('backend/app/config.py'),
  /https:\/\/corepet\.com\.br/,
  'backend default CORS examples should include corepet.com.br',
);

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
