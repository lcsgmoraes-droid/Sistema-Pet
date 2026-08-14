import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import {
  BILLING_ACCEPTANCE_TEXT,
  BILLING_CONTRACT_DOCUMENT_SHA256,
  BILLING_CONTRACT_VERSION,
  billingContract,
} from "../src/data/billingContract.js";

const calculatedHash = createHash("sha256")
  .update(JSON.stringify(billingContract), "utf8")
  .digest("hex");

assert.equal(calculatedHash, BILLING_CONTRACT_DOCUMENT_SHA256);
assert.equal(billingContract.version, `Versão ${BILLING_CONTRACT_VERSION}`);
assert.match(BILLING_ACCEPTANCE_TEXT, /autorizo a cobrança correspondente/);
assert.ok(
  billingContract.sections.some((section) =>
    section.title.toLocaleLowerCase("pt-BR").includes("reajuste anual"),
  ),
);

const meuPlano = await readFile(new URL("../src/pages/MeuPlano.jsx", import.meta.url), "utf8");
const publicRoutes = await readFile(
  new URL("../src/app/routes/PublicRoutes.jsx", import.meta.url),
  "utf8",
);
const backendContract = await readFile(
  new URL("../../backend/app/services/billing_contract_service.py", import.meta.url),
  "utf8",
);

assert.match(publicRoutes, /path="\/contrato-assinatura"/);
assert.match(meuPlano, /accepted: true/);
assert.match(meuPlano, /contract_document_sha256: BILLING_CONTRACT_DOCUMENT_SHA256/);
assert.ok(backendContract.includes(`CONTRACT_VERSION = "${BILLING_CONTRACT_VERSION}"`));
assert.ok(backendContract.includes(BILLING_CONTRACT_DOCUMENT_SHA256));

console.log("Billing contract and acceptance contract OK");
