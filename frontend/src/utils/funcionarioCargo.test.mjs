import assert from "node:assert/strict";
import { test } from "node:test";

import { formatarCargoFuncionario } from "./funcionarioCargo.js";

test("mantem string como esta (formato de /comissoes/configuracoes/funcionarios)", () => {
  assert.equal(formatarCargoFuncionario("cliente / funcionario"), "cliente / funcionario");
  assert.equal(formatarCargoFuncionario(""), "");
});

test("extrai .nome de objeto cargo (formato de /funcionarios)", () => {
  assert.equal(
    formatarCargoFuncionario({ id: 1, nome: "Vendedor", salario_base: 2000 }),
    "Vendedor",
  );
});

test("objeto sem nome vira string vazia, nunca quebra", () => {
  assert.equal(formatarCargoFuncionario({ id: 1 }), "");
});

test("null/undefined viram string vazia", () => {
  assert.equal(formatarCargoFuncionario(null), "");
  assert.equal(formatarCargoFuncionario(undefined), "");
});
