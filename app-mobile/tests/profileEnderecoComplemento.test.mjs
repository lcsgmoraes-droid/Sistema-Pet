import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(__dirname, "..");

function read(relativePath) {
  return readFileSync(path.join(appRoot, relativePath), "utf8");
}

test("perfil mobile edita e salva complemento do endereco padrao", () => {
  const source = read("src/screens/profile/ProfileScreen.tsx");
  const addressSections = read(
    "src/screens/profile/profile/ProfileAddressSections.tsx",
  );

  assert.match(source, /useState\(user\?\.complemento \?\? ""\)/);
  assert.match(source, /setComplemento\(user\?\.complemento \?\? ""\)/);
  assert.match(source, /complemento:\s*complemento\.trim\(\) \|\| undefined/);
  assert.match(addressSections, /<Campo label="Complemento">/);
  assert.match(source, /user\?\.complemento/);
});

test("checkout mobile usa complemento do endereco salvo", () => {
  const source = read("src/screens/shop/CartScreen.tsx");
  const utils = read("src/screens/shop/cart/CartUtils.ts");

  assert.match(utils, /complemento: user\?\.complemento \?\? ""/);
  assert.match(source, /useState\(enderecoInicial\.complemento\)/);
});

test("perfil mobile edita e salva complemento do endereco de entrega", () => {
  const source = read("src/screens/profile/ProfileScreen.tsx");
  const addressSections = read(
    "src/screens/profile/profile/ProfileAddressSections.tsx",
  );

  assert.match(source, /user\?\.endereco_entrega_detalhado \?\? \{\}/);
  assert.match(
    source,
    /useState\(\s*Boolean\(user\?\.usar_endereco_entrega_diferente\),?\s*\)/,
  );
  assert.match(source, /entrega_complemento:\s*entregaComplemento\.trim\(\) \|\| undefined/);
  assert.match(addressSections, /<Campo label="Complemento da entrega">/);
});

test("checkout mobile prefere complemento do endereco de entrega detalhado", () => {
  const source = read("src/screens/shop/cart/CartUtils.ts");

  assert.match(source, /user\?\.endereco_entrega_detalhado/);
  assert.match(source, /user\?\.usar_endereco_entrega_diferente/);
  assert.match(source, /entrega_complemento/);
});

test("tipo do usuario mobile declara complemento", () => {
  const source = read("src/types/index.ts");

  assert.match(source, /complemento\?: string \| null;/);
  assert.match(source, /usar_endereco_entrega_diferente\?: boolean \| null;/);
  assert.match(source, /endereco_entrega_detalhado\?: EcommerceDeliveryAddress \| null;/);
  assert.match(source, /entrega_complemento\?: string \| null;/);
});
