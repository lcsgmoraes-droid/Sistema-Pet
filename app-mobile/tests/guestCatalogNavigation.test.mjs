import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, '..', relativePath), 'utf8');
}

test('visitante entra no app principal depois de selecionar a loja', () => {
  const appNavigator = source('src/navigation/AppNavigator.tsx');

  assert.doesNotMatch(appNavigator, /activeNav\s*=\s*<AuthNavigator/);
  assert.match(appNavigator, /activeNav\s*=\s*<MainNavigator/);
  assert.match(appNavigator, /AppTabs/);
});

test('login fica disponivel sob demanda no navegador do cliente', () => {
  const mainNavigator = source('src/navigation/MainNavigator.tsx');

  assert.match(mainNavigator, /name="AppTabs"/);
  assert.match(mainNavigator, /name="Login"/);
  assert.match(mainNavigator, /protectTab/);
  assert.match(mainNavigator, /navigateToLogin/);
});

test('catalogo e detalhes protegem somente acoes de conta', () => {
  const catalog = source('src/screens/shop/CatalogScreen.tsx');
  const detail = source('src/screens/shop/ProductDetailScreen.tsx');

  assert.match(catalog, /useRequireAuth/);
  assert.match(catalog, /onOpenProduct=/);
  assert.match(catalog, /Faca login para adicionar produtos ao carrinho/);
  assert.match(catalog, /Faca login para salvar produtos nos favoritos/);
  assert.match(detail, /useRequireAuth/);
  assert.match(detail, /Faca login para adicionar produtos ao carrinho/);
});

test('inicio nao consulta notificacoes para visitante e oferece entrada', () => {
  const home = source('src/screens/HomeScreen.tsx');

  assert.match(home, /if \(!isAuthenticated\)/);
  assert.match(home, /Continuar explorando sem login|Explore os produtos da loja/);
  assert.match(home, /navigateToLogin/);
});
