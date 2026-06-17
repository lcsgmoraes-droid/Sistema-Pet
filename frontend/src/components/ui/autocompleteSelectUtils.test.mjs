import assert from "node:assert/strict";
import test from "node:test";

import {
  filtrarOpcoesAutocomplete,
  normalizarTextoAutocomplete,
} from "./autocompleteSelectUtils.js";

test("normalizarTextoAutocomplete ignora acentos e caixa", () => {
  assert.equal(normalizarTextoAutocomplete("Clínico Geral"), "clinico geral");
});

test("filtrarOpcoesAutocomplete filtra por texto digitado em label e meta", () => {
  const opcoes = [
    { id: 1, nome: "Dipirona", principio_ativo: "Metamizol" },
    { id: 2, nome: "Amoxicilina", principio_ativo: "Clavulanato" },
    { id: 3, nome: "Furosemida", principio_ativo: "Diuretico" },
  ];

  const filtradas = filtrarOpcoesAutocomplete({
    termo: "clavu",
    options: opcoes,
    getOptionLabel: (opcao) => opcao.nome,
    getOptionMeta: (opcao) => opcao.principio_ativo,
  });

  assert.deepEqual(
    filtradas.map((opcao) => opcao.nome),
    ["Amoxicilina"],
  );
});
