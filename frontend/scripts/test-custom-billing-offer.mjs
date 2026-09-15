import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const publicRoutes = read("src/app/routes/PublicRoutes.jsx");
const lazyPages = read("src/app/lazyPages.jsx");
const publicPage = read("src/pages/BillingOfferPublicPage.jsx");
const opsPanel = read("src/pages/ops-tenants/OpsTenantBillingOfferPanel.jsx");
const opsController = read("src/pages/ops-tenants/useOpsTenantsController.js");
const api = read("src/api.js");
const backendModel = read("../backend/app/billing_models.py");
const backendOfferService = read("../backend/app/services/billing_offer_service.py");
const migration = read(
  "../backend/alembic/versions/zzq20260914a1_billing_offer_commercial_terms.py",
);

assert.match(publicRoutes, /path="\/contratar\/:token"/);
assert.match(lazyPages, /BillingOfferPublicPage/);
assert.match(publicPage, /offers\/public\/\$\{encodeURIComponent\(token\)\}\/accept/);
assert.match(publicPage, /BILLING_CONTRACT_DOCUMENT_SHA256/);
assert.match(publicPage, /representative_name/);
assert.match(publicPage, /Abrir pagamento no Asaas/);
assert.match(publicPage, /Condições específicas/);
assert.match(publicPage, /não inclui SLA contratual/);
assert.match(opsPanel, /Mensalidade personalizada/);
assert.match(opsPanel, /Módulos extras ao plano-base/);
assert.match(opsPanel, /Escopo contratado/);
assert.match(opsPanel, /Fora do escopo e dependências/);
assert.match(opsPanel, /Desenvolvimento sob medida/);
assert.match(opsController, /price_cents: priceCents/);
assert.match(opsController, /extra_modules: billingOfferForm\.extra_modules/);
assert.match(opsController, /scope_summary: billingOfferForm\.scope_summary/);
assert.match(backendModel, /commercial_terms_json/);
assert.match(backendOfferService, /contractual_sla_included/);
assert.match(backendOfferService, /Esta proposta foi criada sem as condições comerciais atuais/);
assert.match(migration, /zzp20260914a1/);
assert.match(api, /"\/contratar"/);

console.log("Custom billing offer checks passed.");
