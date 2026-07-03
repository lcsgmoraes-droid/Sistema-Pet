import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function exists(relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function lineCount(relativePath) {
  return read(relativePath).split(/\r?\n/).length;
}

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (["node_modules", "dist", "build"].includes(entry.name)) return [];
      return walk(fullPath);
    }
    return [fullPath];
  });
}

const targetFiles = [
  "src/components/VendasFinanceiro.jsx",
  "src/components/ModalFecharCaixa.jsx",
  "src/pages/comissoes/RelatoriosComissoes.jsx",
  "src/components/EstoqueBling.jsx",
  "src/components/MovimentacoesProduto.jsx",
];

const extractedFiles = [
  "src/components/financeiro/VendasFinanceiroView.jsx",
  "src/components/caixa/ModalFecharCaixaContent.jsx",
  "src/pages/comissoes/relatorios/RelatoriosComissoesDreSection.jsx",
  "src/components/estoqueBling/estoqueBlingNormalizers.js",
  "src/components/estoque/MovimentacoesProdutoModals.jsx",
];

for (const relativePath of extractedFiles) {
  assert(exists(relativePath), `Missing extracted frontend refactor file: ${relativePath}`);
}

for (const relativePath of targetFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 1000, `${relativePath} has ${lines} lines; expected <= 1000`);
}

for (const relativePath of extractedFiles) {
  const lines = lineCount(relativePath);
  assert(lines <= 900, `${relativePath} has ${lines} lines; expected <= 900`);
}

const sourceFiles = walk(path.join(root, "src"))
  .filter((filePath) => /\.(js|jsx|ts|tsx)$/.test(filePath))
  .map((filePath) => path.relative(root, filePath).replaceAll(path.sep, "/"));

const oversized = sourceFiles
  .map((relativePath) => [relativePath, lineCount(relativePath)])
  .filter(([, lines]) => lines > 1000);

assert(
  oversized.length === 0,
  `frontend/src still has files above 1000 lines: ${oversized
    .map(([relativePath, lines]) => `${relativePath}=${lines}`)
    .join(", ")}`,
);

const vendasFinanceiro = read("src/components/VendasFinanceiro.jsx");
assert(
  vendasFinanceiro.includes("./financeiro/VendasFinanceiroView"),
  "VendasFinanceiro.jsx should delegate its visual composition to VendasFinanceiroView",
);

const modalFecharCaixa = read("src/components/ModalFecharCaixa.jsx");
assert(
  modalFecharCaixa.includes("./caixa/ModalFecharCaixaContent"),
  "ModalFecharCaixa.jsx should delegate its modal markup to ModalFecharCaixaContent",
);

const relatoriosComissoes = read("src/pages/comissoes/RelatoriosComissoes.jsx");
assert(
  relatoriosComissoes.includes("./relatorios/RelatoriosComissoesSections"),
  "RelatoriosComissoes.jsx should delegate report sections to RelatoriosComissoesSections",
);

const relatoriosComissoesSections = read(
  "src/pages/comissoes/relatorios/RelatoriosComissoesSections.jsx",
);
assert(
  relatoriosComissoesSections.includes("./RelatoriosComissoesDreSection"),
  "RelatoriosComissoesSections.jsx should delegate DRE rendering to RelatoriosComissoesDreSection",
);

const estoqueBling = read("src/components/EstoqueBling.jsx");
assert(
  estoqueBling.includes("./estoqueBling/estoqueBlingNormalizers"),
  "EstoqueBling.jsx should delegate payload normalization to estoqueBlingNormalizers",
);

const movimentacoesProduto = read("src/components/MovimentacoesProduto.jsx");
assert(
  movimentacoesProduto.includes("./estoque/MovimentacoesProdutoModals"),
  "MovimentacoesProduto.jsx should delegate modal composition to MovimentacoesProdutoModals",
);
assert(
  movimentacoesProduto.includes("/estoque/sync/vincular-automatico/"),
  "MovimentacoesProduto.jsx should allow forcing a Bling link for one product",
);
const movimentacoesProdutoHeader = read("src/components/estoque/MovimentacoesProdutoHeader.jsx");
assert(
  movimentacoesProdutoHeader.includes("Forcar vinculo"),
  "MovimentacoesProdutoHeader.jsx should expose the force-link label when product has no Bling link",
);

console.log("Frontend zero large files refactor contract OK");
