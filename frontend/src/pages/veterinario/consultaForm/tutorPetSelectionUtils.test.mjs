import assert from "node:assert/strict";
import test from "node:test";

import { filtrarTutoresPorTermo } from "./tutorPetSelectionUtils.js";

const tutores = [
  { id: 1, nome: "Ana Souza", telefone: "11999990000", celular: "" },
  { id: 2, nome: "Maria Oliveira", telefone: "", celular: "21988887777" },
  { id: 3, nome: "Carlos Santos", telefone: "", celular: "" },
];

test("filtrarTutoresPorTermo nao lista tutores antes do termo minimo", () => {
  assert.deepEqual(filtrarTutoresPorTermo(tutores, ""), []);
  assert.deepEqual(filtrarTutoresPorTermo(tutores, "a"), []);
});

test("filtrarTutoresPorTermo lista tutores quando a busca tem termo suficiente", () => {
  const resultado = filtrarTutoresPorTermo(tutores, "ma");

  assert.deepEqual(
    resultado.map((tutor) => tutor.nome),
    ["Maria Oliveira"],
  );
});
