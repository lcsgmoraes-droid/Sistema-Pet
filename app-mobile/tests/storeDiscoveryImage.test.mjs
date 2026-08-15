import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

test("lista de lojas mostra a imagem publica e usa icone se ela falhar", () => {
  const tenantStore = source("src/store/tenant.store.ts");
  const storeSelection = source("src/screens/SelecionarLojaScreen.tsx");

  assert.match(tenantStore, /imagem_url\?:\s*string\s*\|\s*null/);
  assert.match(
    storeSelection,
    /resolveTenantAssetUrl\(store\.imagem_url\s*\?\?\s*store\.logo_url\)/,
  );
  assert.match(storeSelection, /onError=\{\(\) => setImageFailed\(true\)\}/);
  assert.match(storeSelection, /name="storefront-outline"/);
});
