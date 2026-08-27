import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const root = path.resolve(import.meta.dirname, "../..");
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8");

test("registra Central de Divulgação e Rastreamento ao Vivo no menu e nas rotas", () => {
  const salesRoutes = read("app/routes/SalesMarketingRoutes.jsx");
  const deliveryRoutes = read("app/routes/DeliveryAiRoutes.jsx");
  const lazyPages = read("app/lazyPages.jsx");
  const menu = read("components/layout/menuConfig.js");

  assert.match(salesRoutes, /path="ecommerce\/divulgacao"/);
  assert.match(deliveryRoutes, /path="entregas\/rastreamento"/);
  assert.match(lazyPages, /export const EcommerceDivulgacao/);
  assert.match(lazyPages, /export const RastreamentoAoVivo/);
  assert.match(menu, /\/ecommerce\/divulgacao/);
  assert.match(menu, /\/entregas\/rastreamento/);
});

test("simulador usa endpoint autenticado e não ganha rota pública própria", () => {
  const page = read("pages/entregas/RastreamentoAoVivo.jsx");
  const publicRoutes = read("app/routes/PublicRoutes.jsx");

  assert.match(page, /simuladorRastreioHabilitado\(import\.meta\.env\)/);
  assert.match(page, /\/rotas-entrega\/\$\{rota\.id\}\/atualizar-localizacao/);
  assert.doesNotMatch(publicRoutes, /simular-deslocamento/);
});
