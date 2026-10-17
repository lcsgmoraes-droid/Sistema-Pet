import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./LembretesValidadeSection.jsx", import.meta.url), "utf8");

test("validade usa componentes v2 de aviso e ação", () => {
  assert.match(source, /FaixaAviso/);
  assert.match(source, /BotaoInteracao/);
  assert.match(source, /BotaoExcluir/);
  assert.doesNotMatch(source, /<button[\s>]/);
});

test("ações de validade usam rótulos operacionais claros", () => {
  assert.match(source, />\s*Descartar\s*</);
  assert.match(source, />\s*Registrar troca\s*</);
  assert.match(source, />\s*Retornar ao estoque\s*</);
});

test("processamento manual preserva o mesmo fluxo do controller", () => {
  assert.match(source, /carregarValidadePendencias\(\{ processar: true, mostrarToast: true \}\)/);
  assert.match(source, /processandoValidade \? "Verificando\.\.\." : "Verificar validade agora"/);
});
