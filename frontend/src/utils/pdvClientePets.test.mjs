import assert from "node:assert/strict";
import { test } from "node:test";
import { incluirPetNoClienteSelecionado } from "./pdvClientePets.js";

test("inclui imediatamente o pet recem-cadastrado no cliente do PDV", () => {
  const cliente = { id: 10, nome: "Maria", pets: [] };
  const pet = { id: 21, cliente_id: 10, nome: "Rex" };

  const atualizado = incluirPetNoClienteSelecionado(cliente, pet);

  assert.deepEqual(atualizado.pets, [pet]);
  assert.deepEqual(cliente.pets, []);
});

test("aceita IDs numericos ou textuais e atualiza o pet sem duplicar", () => {
  const cliente = {
    id: "10",
    pets: [{ id: 21, cliente_id: 10, nome: "Rex", peso: 4 }],
  };
  const pet = { id: "21", tutor_id: "10", nome: "Rex", peso: 5 };

  const atualizado = incluirPetNoClienteSelecionado(cliente, pet);

  assert.equal(atualizado.pets.length, 1);
  assert.equal(atualizado.pets[0].peso, 5);
});

test("nao mistura pet de outro tutor na venda atual", () => {
  const cliente = { id: 10, pets: [] };
  const pet = { id: 21, cliente_id: 99, nome: "Rex" };

  assert.equal(incluirPetNoClienteSelecionado(cliente, pet), cliente);
});
