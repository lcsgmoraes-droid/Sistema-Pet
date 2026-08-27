import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ts = require("typescript");
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function source(relativePath) {
  return readFileSync(path.resolve(__dirname, "..", relativePath), "utf8");
}

function carregarUtilsPdv() {
  const compilado = ts.transpileModule(source("src/screens/funcionario/pdv/FuncionarioPdvUtils.ts"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const modulo = { exports: {} };
  Function("exports", "module", compilado)(modulo.exports, modulo);
  return modulo.exports;
}

const utils = carregarUtilsPdv();
const produto = {
  id: 1,
  nome: "Racao teste",
  preco_venda: 100,
  estoque_atual: 10,
  vendavel: true,
};

test("edicao do item aceita preco, quantidade e desconto percentual", () => {
  const item = utils.criarItemCarrinhoPdv(produto);
  const atualizado = utils.atualizarItemCarrinhoPdv(item, {
    precoUnitario: 80,
    quantidade: 2,
    tipoDesconto: "percentual",
    valorDesconto: 10,
  });

  assert.equal(utils.subtotalBrutoItemPdv(atualizado), 160);
  assert.equal(utils.descontoItemPdv(atualizado), 16);
  assert.equal(utils.subtotalLiquidoItemPdv(atualizado), 144);
});

test("desconto total e rateado sem perder centavos", () => {
  const itens = [
    utils.criarItemCarrinhoPdv(produto),
    utils.criarItemCarrinhoPdv({ ...produto, id: 2, preco_venda: 50 }),
  ];
  const atualizados = utils.aplicarDescontoTotalPdv(itens, "valor", 10.01);

  assert.equal(
    atualizados.reduce((soma, item) => soma + utils.descontoItemPdv(item), 0),
    10.01,
  );
  assert.equal(
    atualizados.reduce((soma, item) => soma + utils.subtotalLiquidoItemPdv(item), 0),
    139.99,
  );
});

test("tela envia desconto por item e abre edicao ao tocar no produto", () => {
  const screen = source("src/screens/funcionario/FuncionarioPdvScreen.tsx");
  const content = source("src/screens/funcionario/pdv/FuncionarioPdvContent.tsx");
  const modals = source("src/screens/funcionario/pdv/FuncionarioPdvDescontoModals.tsx");

  assert.match(screen, /desconto_item:\s*descontoItemPdv\(item\)/);
  assert.match(content, /onPress=\{\(\) => abrirEdicaoItem\(item\)\}/);
  assert.match(content, /Desconto no total/);
  assert.match(modals, /Alterar item da venda/);
  assert.match(modals, /Tipo de desconto/);
});
