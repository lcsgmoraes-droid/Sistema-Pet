import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function exists(relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function lineCount(relativePath) {
  return read(relativePath).split(/\r?\n/).length;
}

const financeFiles = [
  "src/components/financeiro/vendasFinanceiroUtils.js",
  "src/components/financeiro/vendasFinanceiro/vendasFinanceiroExcel.js",
  "src/components/financeiro/vendasFinanceiro/vendasFinanceiroDatas.js",
  "src/components/financeiro/vendasFinanceiro/vendasFinanceiroRelatorio.js",
  "src/components/financeiro/vendasFinanceiro/vendasFinanceiroAnalises.js",
  "src/components/financeiro/vendasFinanceiro/vendasFinanceiroTotalizadores.js",
];

const transferenciaFiles = [
  "src/pages/EstoqueTransferenciaParceiro.jsx",
  "src/pages/estoqueTransferenciaParceiro/EstoqueTransferenciaParceiroPage.jsx",
  "src/pages/estoqueTransferenciaParceiro/useEstoqueTransferenciaParceiroController.js",
  "src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaResults.jsx",
  "src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaBulkActions.jsx",
  "src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaLista.jsx",
  "src/pages/estoqueTransferenciaParceiro/HistoricoTransferenciaBaixaPanel.jsx",
];

const transferenciaSupportFiles = [
  "src/pages/estoqueTransferenciaParceiro/useTransferenciaLancamentoController.js",
  "src/pages/estoqueTransferenciaParceiro/useTransferenciaHistoricoController.js",
];

for (const relativePath of [...financeFiles, ...transferenciaFiles, ...transferenciaSupportFiles]) {
  assert(exists(relativePath), `Missing extracted refactor file: ${relativePath}`);
}

for (const relativePath of [...financeFiles, ...transferenciaFiles]) {
  const lines = lineCount(relativePath);
  assert(lines <= 420, `${relativePath} has ${lines} lines; expected <= 420`);
}

for (const relativePath of transferenciaSupportFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 620, `${relativePath} has ${lines} lines; expected <= 620`);
}

const financeFacade = read("src/components/financeiro/vendasFinanceiroUtils.js");
assert(
  financeFacade.includes("vendasFinanceiro/vendasFinanceiroExcel"),
  "vendasFinanceiroUtils.js should re-export the extracted Excel helpers",
);
assert(
  financeFacade.includes("vendasFinanceiro/vendasFinanceiroDatas"),
  "vendasFinanceiroUtils.js should re-export the extracted date helpers",
);
assert(
  financeFacade.includes("vendasFinanceiro/vendasFinanceiroRelatorio"),
  "vendasFinanceiroUtils.js should re-export the extracted report helpers",
);
assert(
  financeFacade.includes("vendasFinanceiro/vendasFinanceiroAnalises"),
  "vendasFinanceiroUtils.js should re-export the extracted analysis helpers",
);
assert(
  financeFacade.includes("vendasFinanceiro/vendasFinanceiroTotalizadores"),
  "vendasFinanceiroUtils.js should re-export the extracted totalizer helpers",
);
assert(!financeFacade.includes("writeExcelFile"), "Finance facade should not own Excel IO");
assert(!financeFacade.includes("function "), "Finance facade should not own business functions");

const financeFeatureSource = financeFiles
  .filter((relativePath) => relativePath !== "src/components/financeiro/vendasFinanceiroUtils.js")
  .map(read)
  .join("\n");

for (const literal of [
  "COLUNAS_RELATORIO_VENDAS",
  "exportarPlanilhasExcel",
  "calcularFiltroRapidoPeriodoVendas",
  "montarFeriadosPeriodoFinanceiro",
  "consolidarFormasRecebimentoFinanceiro",
  "calcularAnaliseInteligenteVendas",
  "montarCardsTotalizadoresListaVendasFinanceiro",
  "calcularAnalisePromocoesFinanceiro",
  "ajustarVendaImposto",
]) {
  assert(financeFeatureSource.includes(literal), `Missing finance behavior literal: ${literal}`);
}

const transferFacade = read("src/pages/EstoqueTransferenciaParceiro.jsx");
assert(
  transferFacade.includes("estoqueTransferenciaParceiro/EstoqueTransferenciaParceiroPage"),
  "EstoqueTransferenciaParceiro.jsx should delegate to the extracted page module",
);
assert(!transferFacade.includes("useState"), "Transfer facade should not own React state");
assert(!transferFacade.includes("api."), "Transfer facade should not own API calls");

const transferPage = read(
  "src/pages/estoqueTransferenciaParceiro/EstoqueTransferenciaParceiroPage.jsx",
);
assert(
  transferPage.includes("useEstoqueTransferenciaParceiroController"),
  "Extracted transfer page should consume the controller hook",
);
assert(
  transferPage.includes("LancamentoTransferenciaParceiro"),
  "Extracted transfer page should keep the launch form composition",
);
assert(
  transferPage.includes("HistoricoTransferenciaResults"),
  "Extracted transfer page should keep the history composition",
);

const transferFeatureSource = transferenciaFiles
  .filter((relativePath) => relativePath !== "src/pages/EstoqueTransferenciaParceiro.jsx")
  .concat(transferenciaSupportFiles)
  .map(read)
  .join("\n");

for (const literal of [
  "/estoque/transferencia-parceiro",
  "/estoque/transferencia-parceiro/historico",
  "/estoque/transferencia-parceiro/pdf-consolidado",
  "/financeiro/formas-pagamento",
  "criarFormTransferencia",
  "montarPayloadTransferencia",
  "montarCupomTransferencia",
  "registrarBaixaTransferencia",
  "HistoricoTransferenciaBulkActions",
  "HistoricoTransferenciaLista",
  "HistoricoTransferenciaBaixaPanel",
]) {
  assert(transferFeatureSource.includes(literal), `Missing transfer behavior literal: ${literal}`);
}

const routesSource = read("src/app/lazyPages.jsx");
assert(
  routesSource.includes("../pages/EstoqueTransferenciaParceiro"),
  "Lazy page import should keep the public EstoqueTransferenciaParceiro route path",
);

console.log("Final GUI large files refactor contract OK");
