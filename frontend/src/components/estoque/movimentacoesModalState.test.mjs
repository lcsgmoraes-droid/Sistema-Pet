import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../MovimentacoesProduto.jsx", import.meta.url), "utf8");

test("incluir lancamento sempre abre um formulario novo", () => {
  assert.match(
    source,
    /const handleIncluirLancamento = \(\) => \{[\s\S]*?abrirModal\(produtoEhGranel \? "balanco" : "entrada"\);[\s\S]*?\n\s{2}\};/,
  );
});

test("fechar modal descarta o lancamento que estava em edicao", () => {
  assert.match(
    source,
    /const fecharModalLancamento = \(\) => \{\s*setShowModal\(false\);\s*setEditingMovimentacao\(null\);\s*\};/,
  );
  assert.match(source, /onCloseLancamento=\{fecharModalLancamento\}/);
});
