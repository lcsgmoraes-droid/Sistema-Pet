import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";
import ts from "typescript";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function carregarModuloTs(relativo) {
  const arquivo = path.resolve(__dirname, "..", relativo);
  const fonte = readFileSync(arquivo, "utf8");
  const { outputText } = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const module = { exports: {} };
  vm.runInNewContext(
    outputText,
    {
      module,
      exports: module.exports,
      require,
      Intl,
    },
    { filename: arquivo },
  );
  return module.exports;
}

const { incrementarProdutoContagemRapida, resolverLeituraProdutoContagem } = carregarModuloTs(
  "src/screens/funcionario/contagem/FuncionarioContagemUtils.ts",
);

function produto(id, nome) {
  return {
    id,
    nome,
    codigo: String(id),
    codigo_barras: String(id),
    gtin_ean: null,
    unidade: "UN",
    preco_custo: 0,
    preco_venda: 0,
    estoque_atual: 0,
    imagem_url: null,
    permite_balanco: true,
  };
}

test("acumula leituras alternadas por produto na contagem rapida", () => {
  const produtoA = produto(101, "Produto A");
  const produtoB = produto(202, "Produto B");

  let itens = [];
  itens = incrementarProdutoContagemRapida(itens, produtoA);
  itens = incrementarProdutoContagemRapida(itens, produtoB);
  itens = incrementarProdutoContagemRapida(itens, produtoA);

  assert.equal(
    JSON.stringify(itens.map((item) => [item.produto.id, item.quantidade])),
    JSON.stringify([
      [101, 2],
      [202, 1],
    ]),
  );
});

test("retorna a quantidade atual do produto capturado", () => {
  const produtoA = produto(101, "Produto A");

  const { itens, quantidadeAtual } = incrementarProdutoContagemRapida([], produtoA, {
    retornarQuantidade: true,
  });

  assert.equal(quantidadeAtual, 1);
  const segundaLeitura = incrementarProdutoContagemRapida(itens, produtoA, {
    retornarQuantidade: true,
  });
  assert.equal(segundaLeitura.quantidadeAtual, 2);
});

test("seleciona produto sem somar quando bipagem rapida esta desativada", () => {
  const produtoA = produto(101, "Produto A");
  const produtoB = produto(202, "Produto B");
  const itens = incrementarProdutoContagemRapida([], produtoA);

  const resultado = resolverLeituraProdutoContagem(itens, produtoB, {
    bipagemRapidaAtiva: false,
    produtoTravado: null,
  });

  assert.equal(resultado.tipo, "manual");
  assert.equal(resultado.produto.id, 202);
  assert.equal(resultado.quantidade, "1");
  assert.equal(JSON.stringify(resultado.itens), JSON.stringify(itens));
});

test("bloqueia leitura de outro produto quando produto esta travado", () => {
  const produtoA = produto(101, "Produto A");
  const produtoB = produto(202, "Produto B");
  const itens = incrementarProdutoContagemRapida([], produtoA);

  const resultado = resolverLeituraProdutoContagem(itens, produtoB, {
    bipagemRapidaAtiva: true,
    produtoTravado: produtoA,
  });

  assert.equal(resultado.tipo, "bloqueado");
  assert.equal(JSON.stringify(resultado.itens), JSON.stringify(itens));
  assert.match(resultado.mensagem, /Produto A/);
});
