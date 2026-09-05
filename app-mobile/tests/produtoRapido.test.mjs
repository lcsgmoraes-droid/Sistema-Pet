import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

const fonte = readFileSync(new URL("../src/utils/produtoRapido.ts", import.meta.url), "utf8");
const compilado = ts.transpileModule(fonte, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const modulo = { exports: {} };
Function("exports", "module", compilado)(modulo.exports, modulo);
const { valorMonetarioProduto, formatarCampoMonetarioProduto, erroCadastroProduto } = modulo.exports;

test("valores monetarios usam virgula fixa e milhares sem perder centavos", () => {
  assert.equal(formatarCampoMonetarioProduto("5"), "0,05");
  assert.equal(formatarCampoMonetarioProduto("0,055"), "0,55");
  assert.equal(formatarCampoMonetarioProduto("0,555"), "5,55");
  assert.equal(formatarCampoMonetarioProduto("1755525"), "17.555,25");
  assert.equal(valorMonetarioProduto("17.555,25"), 17555.25);
  assert.equal(valorMonetarioProduto("0,01"), 0.01);
});

test("limpar campo permite deixar custo opcional e substituir valor", () => {
  assert.equal(formatarCampoMonetarioProduto(""), "");
  assert.equal(valorMonetarioProduto(""), 0);
  assert.equal(formatarCampoMonetarioProduto("100"), "1,00");
});

test("erro de rede ou validacao estruturada tem mensagem legivel", () => {
  assert.equal(erroCadastroProduto(new Error("Network Error"), "Tente novamente"), "Tente novamente");
  assert.equal(erroCadastroProduto({ response: { data: { detail: [{ msg: "Invalid" }] } } }, "Revise os dados"), "Revise os dados");
  assert.equal(erroCadastroProduto({ response: { data: { detail: "Sem acesso" } } }, "Erro"), "Sem acesso");
});
