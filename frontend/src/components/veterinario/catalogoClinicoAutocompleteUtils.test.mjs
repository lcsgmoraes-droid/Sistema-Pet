import assert from "node:assert/strict";
import test from "node:test";

import {
  filtrarCatalogoClinico,
  montarOpcoesCatalogoClinico,
} from "./catalogoClinicoAutocompleteUtils.js";

test("montarOpcoesCatalogoClinico combina medicamentos e procedimentos com tipo", () => {
  const opcoes = montarOpcoesCatalogoClinico({
    medicamentos: [{ id: 1, nome: "Dipirona", principio_ativo: "Metamizol" }],
    procedimentos: [{ id: 7, nome: "Curativo", descricao: "Troca de curativo" }],
  });

  assert.deepEqual(
    opcoes.map((opcao) => opcao.valor),
    ["med:1", "proc:7"],
  );
  assert.deepEqual(
    opcoes.map((opcao) => opcao.tipo),
    ["medicamento", "procedimento"],
  );
});

test("filtrarCatalogoClinico busca por nome, principio ativo, descricao e ignora acentos", () => {
  const opcoes = montarOpcoesCatalogoClinico({
    medicamentos: [{ id: 1, nome: "Dipirona", principio_ativo: "Metamizol" }],
    procedimentos: [{ id: 7, nome: "Aplicacao subcutanea", descricao: "Injecao SC" }],
  });

  assert.deepEqual(
    filtrarCatalogoClinico(opcoes, "metam").map((opcao) => opcao.label),
    ["Dipirona"],
  );
  assert.deepEqual(
    filtrarCatalogoClinico(opcoes, "injeção").map((opcao) => opcao.label),
    ["Aplicacao subcutanea"],
  );
});
