import assert from "node:assert/strict";
import test from "node:test";

import {
  montarPayloadConsultorioAgenda,
  inserirConsultorioAgenda,
} from "./agendaConsultoriosUtils.js";

test("montarPayloadConsultorioAgenda limpa campos antes de criar", () => {
  assert.deepEqual(
    montarPayloadConsultorioAgenda({
      nome: "  Sala 2  ",
      descricao: "  Atendimento clinico  ",
      ordem: " 3 ",
    }),
    {
      nome: "Sala 2",
      descricao: "Atendimento clinico",
      ordem: 3,
    },
  );
});

test("montarPayloadConsultorioAgenda omite campos opcionais vazios", () => {
  assert.deepEqual(
    montarPayloadConsultorioAgenda({
      nome: "Sala 1",
      descricao: " ",
      ordem: "",
    }),
    {
      nome: "Sala 1",
    },
  );
});

test("inserirConsultorioAgenda atualiza lista sem duplicar e mantendo ordem", () => {
  const atual = [
    { id: 2, nome: "Sala 2", ordem: 2, ativo: true },
    { id: 1, nome: "Sala 1", ordem: 1, ativo: true },
  ];

  assert.deepEqual(
    inserirConsultorioAgenda(atual, { id: 3, nome: "Sala 0", ordem: 0, ativo: true }),
    [
      { id: 3, nome: "Sala 0", ordem: 0, ativo: true },
      { id: 1, nome: "Sala 1", ordem: 1, ativo: true },
      { id: 2, nome: "Sala 2", ordem: 2, ativo: true },
    ],
  );

  assert.deepEqual(
    inserirConsultorioAgenda(atual, { id: 2, nome: "Sala 2 atualizada", ordem: 2, ativo: true }),
    [
      { id: 1, nome: "Sala 1", ordem: 1, ativo: true },
      { id: 2, nome: "Sala 2 atualizada", ordem: 2, ativo: true },
    ],
  );
});
