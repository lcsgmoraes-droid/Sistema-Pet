import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./ClientesNovoTabelaSection.jsx", import.meta.url), "utf8");

test("lista de pessoas reutiliza o icone de copia do sistema", () => {
  assert.match(source, /import CopyableValue from "\.\.\/ui\/CopyableValue"/);
  assert.match(source, /title="Copiar codigo"/);
  assert.match(source, /title="Copiar nome"/);
  assert.match(source, /title="Copiar celular"/);
});

test("copia fica disponivel no desktop e no cartao mobile", () => {
  assert.ok((source.match(/<CopyableValue/g) || []).length >= 6);
  assert.match(source, /buttonClassName="rounded-md p-1/);
});
