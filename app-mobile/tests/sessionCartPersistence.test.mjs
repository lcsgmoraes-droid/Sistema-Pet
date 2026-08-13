import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

test("app mobile guarda e rotaciona access e refresh tokens", () => {
  const storage = source("src/services/authTokenStorage.ts");
  const auth = source("src/services/auth.service.ts");
  const types = source("src/types/index.ts");

  assert.match(types, /refresh_token\?:\s*string\s*\|\s*null/);
  assert.match(storage, /auth_refresh_token/);
  assert.match(storage, /storeAuthTokens/);
  assert.doesNotMatch(
    storage,
    /else if \(accessToken\)[^]*deleteItemAsync\(REFRESH_TOKEN_KEY\)/,
  );
  assert.match(auth, /storeAuthTokens\(data\)/);
});

test("401 renova a sessao uma vez e repete a requisicao original", () => {
  const api = source("src/services/api.ts");

  assert.match(api, /\/ecommerce\/auth\/refresh/);
  assert.match(api, /refreshPromise/);
  assert.match(api, /_sessionRefreshRetried/);
  assert.match(api, /return api\.request\(config\)/);
  assert.match(api, /storeAuthTokens/);
  assert.match(api, /isPublicAuthRequest\(config\?\.url\)/);
  assert.doesNotMatch(api, /requestUsedAuthentication/);
});

test("aba Loja usa fachada e preserva badge de itens do carrinho", () => {
  const navigator = source("src/navigation/MainNavigator.tsx");

  assert.match(navigator, /function StoreIcon/);
  assert.match(navigator, /name="storefront-outline"/);
  assert.match(navigator, /const count = totalItens\(\)/);
  assert.doesNotMatch(navigator, /function CartIcon/);
});

test("falha temporaria nao apaga a sessao do cliente", () => {
  const api = source("src/services/api.ts");
  const authStore = source("src/store/auth.store.ts");

  assert.match(api, /refreshWasRejected\(refreshError\)/);
  assert.match(api, /Falhas temporarias de rede\/servidor nao devem deslogar/);
  assert.match(authStore, /hasStoredSession/);
  assert.match(authStore, /getCachedUser/);
  assert.match(authStore, /isAuthenticated:\s*true/);
});

test("carrinho local e separado por usuario e loja", () => {
  const persistence = source("src/services/cartPersistence.ts");

  assert.match(persistence, /context\.tenantId/);
  assert.match(persistence, /context\.userId/);
  assert.match(persistence, /AsyncStorage\.setItem/);
  assert.match(persistence, /AsyncStorage\.getItem/);
});

test("carrinho e reidratado e reconciliado depois de reabrir ou relogar", () => {
  const cartStore = source("src/store/cart.store.ts");
  const appNavigator = source("src/navigation/AppNavigator.tsx");
  const cartScreen = source("src/screens/shop/CartScreen.tsx");

  assert.match(cartStore, /loadCartSnapshot/);
  assert.match(cartStore, /saveCartSnapshot/);
  assert.match(cartStore, /cached\?\.itens\.length/);
  assert.match(
    cartStore,
    /ShopService\.adicionarAoCarrinho\([^]*item\.produto_id[^]*item\.quantidade/,
  );
  assert.match(
    appNavigator,
    /carregar\(\{ userId: user\.id, tenantId: tenant\.id \}\)/,
  );
  assert.match(cartScreen, /useFocusEffect/);
});

test("imagem do carrinho recebida do servidor usa URL completa", () => {
  const shopService = source("src/services/shop.service.ts");

  assert.match(
    shopService,
    /foto_url:\s*resolveMediaUrl\(item\.foto_url\s*\?\?\s*item\.imagem_principal\)/,
  );
});
