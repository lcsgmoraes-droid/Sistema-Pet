import assert from "node:assert/strict";

import {
  criarFiltrosContasPagarDaUrl,
  montarParamsFiltrosContasPagar,
} from "../src/components/contas-pagar/contasPagarFilterHelpers.js";
import {
  criarFiltrosContasReceberDaUrl,
  montarParamsFiltrosContasReceber,
} from "../src/components/contasReceber/contasReceberFilterHelpers.js";
import { normalizarVisaoDashboardClientes } from "../src/pages/clientes/clientesDashboardFilters.js";

const pagarVencidas = criarFiltrosContasPagarDaUrl(new URLSearchParams("filtro=vencidas"));
assert.equal(pagarVencidas.apenas_vencidas, true);
assert.equal(pagarVencidas.data_inicio, "");
assert.equal(pagarVencidas.ocultar_taxas_cartao, false);
assert.equal(montarParamsFiltrosContasPagar(pagarVencidas).get("apenas_vencidas"), "true");

const pagarHoje = criarFiltrosContasPagarDaUrl(new URLSearchParams("filtro=vence_hoje"));
assert.equal(pagarHoje.vence_hoje, true);
assert.equal(montarParamsFiltrosContasPagar(pagarHoje).get("vence_hoje"), "true");

const pagarAbertas = criarFiltrosContasPagarDaUrl(new URLSearchParams("filtro=em_aberto"));
assert.equal(pagarAbertas.status, "em_aberto");

const receberVencidas = criarFiltrosContasReceberDaUrl(new URLSearchParams("filtro=vencidas"));
assert.equal(receberVencidas.apenas_vencidas, true);
assert.equal(montarParamsFiltrosContasReceber(receberVencidas).get("apenas_vencidas"), "true");

const receberAbertas = criarFiltrosContasReceberDaUrl(new URLSearchParams("filtro=em_aberto"));
assert.equal(receberAbertas.status, "em_aberto");

assert.equal(
  normalizarVisaoDashboardClientes(new URLSearchParams("visao=vip_em_risco")),
  "vip_em_risco",
);
assert.equal(
  normalizarVisaoDashboardClientes(new URLSearchParams("visao=novos_promissores")),
  "novos_promissores",
);
assert.equal(
  normalizarVisaoDashboardClientes(new URLSearchParams("visao=sem_whatsapp")),
  "sem_whatsapp",
);
assert.equal(normalizarVisaoDashboardClientes(new URLSearchParams("visao=invalida")), "");

console.log("OK: filtros contextuais do dashboard validados.");
