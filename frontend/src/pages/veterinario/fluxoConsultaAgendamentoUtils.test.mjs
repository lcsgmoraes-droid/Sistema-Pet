import assert from "node:assert/strict";
import test from "node:test";

import {
  buildConsultaPayloadFromAgendamento,
  filtrarAgendamentosClinicosAbertos,
  getAgendamentoConsultaActionLabel,
} from "./fluxoConsultaAgendamentoUtils.js";

test("buildConsultaPayloadFromAgendamento preserva dados clinicos do agendamento", () => {
  assert.deepEqual(
    buildConsultaPayloadFromAgendamento({
      id: 42,
      pet_id: 1150,
      cliente_id: 77,
      veterinario_id: 9,
      tipo: "retorno",
      motivo: "Reavaliar inflamacao intestinal",
    }),
    {
      pet_id: 1150,
      cliente_id: 77,
      veterinario_id: 9,
      tipo: "retorno",
      agendamento_id: 42,
      queixa_principal: "Reavaliar inflamacao intestinal",
    },
  );
});

test("buildConsultaPayloadFromAgendamento omite campos opcionais vazios", () => {
  assert.deepEqual(
    buildConsultaPayloadFromAgendamento({
      id: 43,
      pet_id: 1150,
      cliente_id: 77,
      tipo: "banho",
      motivo: "  ",
    }),
    {
      pet_id: 1150,
      cliente_id: 77,
      tipo: "consulta",
      agendamento_id: 43,
    },
  );
});

test("filtrarAgendamentosClinicosAbertos mostra apenas consultas e retornos acionaveis", () => {
  const agendamentos = [
    { id: 1, tipo: "consulta", status: "agendado", data_hora: "2026-05-17T18:00:00" },
    { id: 2, tipo: "retorno", status: "em_atendimento", data_hora: "2026-05-17T17:30:00" },
    { id: 3, tipo: "vacina", status: "agendado", data_hora: "2026-05-17T09:00:00" },
    { id: 4, tipo: "consulta", status: "cancelado", data_hora: "2026-05-17T10:00:00" },
    { id: 5, tipo: "consulta", status: "finalizado", data_hora: "2026-05-17T11:00:00" },
  ];

  assert.deepEqual(
    filtrarAgendamentosClinicosAbertos(agendamentos).map((item) => item.id),
    [2, 1],
  );
});

test("getAgendamentoConsultaActionLabel diferencia iniciar e continuar", () => {
  assert.equal(getAgendamentoConsultaActionLabel({ tipo: "consulta" }), "Iniciar consulta");
  assert.equal(getAgendamentoConsultaActionLabel({ tipo: "retorno" }), "Iniciar retorno");
  assert.equal(
    getAgendamentoConsultaActionLabel({ tipo: "consulta", consulta_id: 16 }),
    "Continuar consulta",
  );
});
