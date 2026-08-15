import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/EcommerceAparencia.jsx"),
  "utf8",
);

assert.match(
  source,
  /imagem da loja no app/,
  "cadastro da logo deve informar que a imagem aparece no aplicativo",
);
assert.match(source, /function AppStoreLogoPreview/, "tela deve oferecer a previa da logo no app");
assert.match(
  source,
  /Lojas mais próximas/,
  "previa deve identificar a area do aplicativo que usa a logo",
);
assert.match(
  source,
  /logoUrl=\{aparencia\.logo_url\}/,
  "previa do app deve usar a logo cadastrada, nao o banner",
);
assert.match(source, /objectFit: "contain"/, "logo deve aparecer inteira no cartao do app");
assert.match(
  source,
  /canvas\.width = drawW;\s+canvas\.height = drawH;/,
  "upload da logo deve preservar a proporcao sem adicionar margens artificiais",
);
assert.match(
  source,
  /o app poderá usar o primeiro banner/,
  "tela deve explicar o comportamento quando a loja ainda nao tem logo",
);
assert.match(source, /storeName=\{tenantContext\.name\}/, "previa deve exibir o nome real da loja");

console.log("E-commerce app logo preview checks passed.");
