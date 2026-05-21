import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./Cargos.jsx", import.meta.url), "utf8");

test("Cargos mostra orientacoes para preenchimento da composicao de remuneracao", () => {
  assert.match(source, /Guia rapido da folha/);
  assert.match(source, /Salario base/);
  assert.match(source, /INSS patronal e FGTS/);
  assert.match(source, /INSS funcionario/);
  assert.match(source, /Regimes sem encargos/);
});
