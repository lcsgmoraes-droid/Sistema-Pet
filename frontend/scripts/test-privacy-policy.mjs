import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const policyPage = await readFile(new URL("../src/pages/LegalPage.jsx", import.meta.url), "utf8");
const authSupport = await readFile(
  new URL("../../backend/app/auth/auth_multitenant_support.py", import.meta.url),
  "utf8",
);
const ecommerceSettings = await readFile(
  new URL("../../backend/app/routes/ecommerce_auth_settings.py", import.meta.url),
  "utf8",
);
const billingContract = await readFile(
  new URL("../../backend/app/services/billing_contract_service.py", import.meta.url),
  "utf8",
);
const webRegister = await readFile(new URL("../src/pages/Register.jsx", import.meta.url), "utf8");
const ecommerceRegister = await readFile(
  new URL("../src/pages/ecommerce/EcommerceAccountAuthCards.jsx", import.meta.url),
  "utf8",
);
const mobileRegister = await readFile(
  new URL("../../app-mobile/src/screens/auth/RegisterScreen.tsx", import.meta.url),
  "utf8",
);

const acceptanceVersion = "privacidade-2026-09-14";
const termsVersion = "termos-2026-09-14";

assert.match(policyPage, /version: "Versao 2026-09-14"/);
assert.match(policyPage, /WCO COMERCIO E IMPORTACAO LTDA/);
assert.match(policyPage, /Dados, finalidades e bases legais/);
assert.match(policyPage, /Fornecedores, destinatarios e integracoes/);
assert.match(policyPage, /Retencao, encerramento e descarte/);
assert.match(policyPage, /DigitalOcean/);
assert.match(policyPage, /Asaas/);
assert.match(policyPage, /OpenAI/);
assert.match(policyPage, /ciclo padrao de 14 dias/);
assert.doesNotMatch(policyPage, /consentimento pode ser usado para aceite de Termos\/Privacidade/i);
assert.doesNotMatch(policyPage, /Informe o maximo de contexto possivel/i);
for (const registerSource of [webRegister, ecommerceRegister, mobileRegister]) {
  assert.match(registerSource, /confirmo que estou ciente da/);
  assert.doesNotMatch(registerSource, /Li e aceito a/);
}

for (const source of [authSupport, ecommerceSettings, billingContract]) {
  assert.ok(source.includes(acceptanceVersion));
  assert.ok(source.includes(termsVersion));
}

console.log("Privacy policy transparency and acceptance version OK");
