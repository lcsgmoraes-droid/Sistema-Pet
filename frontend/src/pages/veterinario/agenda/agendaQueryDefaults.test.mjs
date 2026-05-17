import assert from "node:assert/strict";
import test from "node:test";

import { aplicarDefaultsQueryAgenda } from "./agendaQueryDefaults.js";

test("aplicarDefaultsQueryAgenda preenche modal aberto por deep link de retorno", () => {
  const hoje = new Date(2026, 4, 17);
  const form = aplicarDefaultsQueryAgenda({
    formAtual: {
      pet_id: "",
      veterinario_id: "",
      consultorio_id: "",
      tipo: "consulta",
      data: "",
      hora: "",
      motivo: "",
      emergencia: false,
    },
    dataBase: hoje,
    tipoQuery: "retorno",
    motivoQuery: "Retorno - Inflamacao no intestino",
    consultaOrigemIdQuery: "16",
  });

  assert.deepEqual(form, {
    pet_id: "",
    veterinario_id: "",
    consultorio_id: "",
    consulta_origem_id: "16",
    tipo: "retorno",
    data: "2026-05-17",
    hora: "",
    motivo: "Retorno - Inflamacao no intestino",
    emergencia: false,
  });
});

test("aplicarDefaultsQueryAgenda preserva campos ja preenchidos e normaliza tipo invalido", () => {
  const form = aplicarDefaultsQueryAgenda({
    formAtual: {
      pet_id: "1150",
      veterinario_id: "9",
      consultorio_id: "2",
      tipo: "consulta",
      data: "2026-05-20",
      hora: "14:30",
      motivo: "Consulta normal",
      emergencia: false,
    },
    dataBase: new Date(2026, 4, 17),
    tipoQuery: "banho",
    motivoQuery: "",
  });

  assert.equal(form.tipo, "consulta");
  assert.equal(form.data, "2026-05-20");
  assert.equal(form.hora, "14:30");
  assert.equal(form.motivo, "Consulta normal");
});

test("aplicarDefaultsQueryAgenda preserva consulta de origem quando reabre modal de retorno", () => {
  const form = aplicarDefaultsQueryAgenda({
    formAtual: {
      pet_id: "1150",
      veterinario_id: "9",
      consultorio_id: "2",
      consulta_origem_id: "",
      tipo: "consulta",
      data: "",
      hora: "",
      motivo: "",
      emergencia: false,
    },
    dataBase: new Date(2026, 4, 17),
    tipoQuery: "retorno",
    motivoQuery: "Retorno",
    consultaOrigemIdQuery: "18",
  });

  assert.equal(form.consulta_origem_id, "18");
  assert.equal(form.tipo, "retorno");
});
