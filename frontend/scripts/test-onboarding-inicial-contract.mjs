import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import {
  SECOES_ONBOARDING,
  buildGuiaHref,
  flattenOnboardingItems,
} from "../src/pages/introducaoGuiada/introducaoGuiadaConfig.js";

const root = process.cwd();

const REQUIRED_SECTIONS = [
  "empresa-acesso",
  "financeiro-obrigatorio",
  "cadastros-base",
  "operacao-venda",
  "compras-estoque",
  "modulos-operacao",
  "validacao-final",
];

const REQUIRED_ITEM_IDS = [
  "empresa-dados",
  "empresa-fiscal",
  "usuarios-permissoes",
  "contas-bancarias",
  "formas-pagamento",
  "operadoras-cartao",
  "categorias-financeiras",
  "dre-tipos-despesa",
  "produtos",
  "pessoas",
  "abrir-caixa",
  "venda-teste",
  "fechar-caixa",
  "compras-entrada-xml",
  "modulo-veterinario",
  "modulo-banho-tosa",
  "validacao-relatorios",
];

const VALID_BADGES = new Set(["obrigatorio", "recomendado", "condicional"]);

assert.equal(Array.isArray(SECOES_ONBOARDING), true, "SECOES_ONBOARDING deve ser array");

for (const sectionId of REQUIRED_SECTIONS) {
  assert(
    SECOES_ONBOARDING.some((section) => section.id === sectionId),
    `Secao obrigatoria ausente: ${sectionId}`,
  );
}

const items = flattenOnboardingItems(SECOES_ONBOARDING);
const itemIds = items.map((item) => item.id);
assert.equal(new Set(itemIds).size, itemIds.length, "IDs dos itens devem ser unicos");

for (const itemId of REQUIRED_ITEM_IDS) {
  assert(itemIds.includes(itemId), `Item obrigatorio ausente: ${itemId}`);
}

for (const item of items) {
  assert(item.titulo, `Item ${item.id} precisa de titulo`);
  assert(item.resultado, `Item ${item.id} precisa de resultado`);
  assert(item.onde?.startsWith("/"), `Item ${item.id} precisa apontar para rota absoluta`);
  assert(VALID_BADGES.has(item.tipo), `Item ${item.id} tem tipo invalido: ${item.tipo}`);
}

assert.equal(
  buildGuiaHref("/cadastros/financeiro/formas-pagamento", "formas-pagamento"),
  "/cadastros/financeiro/formas-pagamento?guia=formas-pagamento",
);
assert.equal(
  buildGuiaHref("/pdv?origem=ajuda", "venda-teste"),
  "/pdv?origem=ajuda&guia=venda-teste",
);

const ajudaSource = fs.readFileSync(
  path.join(root, "src/pages/centralAjuda/centralAjudaKnowledge.js"),
  "utf8",
);

for (const requiredText of [
  "Primeiros passos para configurar o Sistema Pet",
  "Financeiro obrigatorio antes da primeira venda",
  "Compras, entrada XML e Bling",
  "/cadastros/financeiro/formas-pagamento",
  "/compras/entrada-xml",
  "/ecommerce/configuracoes",
]) {
  assert(ajudaSource.includes(requiredText), `Central de Ajuda sem texto: ${requiredText}`);
}

console.log("Onboarding inicial contract OK");
