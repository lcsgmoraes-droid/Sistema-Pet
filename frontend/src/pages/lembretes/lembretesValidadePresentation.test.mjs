import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./LembretesValidadeSection.jsx", import.meta.url), "utf8");

test("validade usa apresentacao clean e acao verde petroleo", () => {
  assert.match(source, /bg-teal-50/);
  assert.match(source, /text-teal-700/);
  assert.match(source, /rounded-full/);
  assert.match(source, /dark:bg-slate-900/);
  assert.match(source, /dark:bg-teal-500\/10/);
  assert.doesNotMatch(source, /className="btn btn-primary"/);
});

test("acoes de validade usam rotulos operacionais claros", () => {
  assert.match(source, />\s*Descartar\s*</);
  assert.match(source, />\s*Registrar troca\s*</);
  assert.match(source, />\s*Retornar ao estoque\s*</);
});

test("processamento manual preserva o mesmo fluxo do controller", () => {
  assert.match(source, /carregarValidadePendencias\(\{ processar: true, mostrarToast: true \}\)/);
  assert.match(source, /processandoValidade \? "Verificando\.\.\." : "Verificar validade agora"/);
});
