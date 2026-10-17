import assert from "node:assert/strict";
import test from "node:test";

import { montarSlotsModal } from "./banhoTosaSlotsModal.js";

const DIA = "2030-10-20";
const BANHEIRA = { id: 1, nome: "Banheira 1", tipo: "banheira", capacidade_simultanea: 1 };

function reserva(inicio, fim, extras = {}) {
  return {
    data_hora_inicio: `${DIA}T${inicio}:00`,
    data_hora_fim_prevista: `${DIA}T${fim}:00`,
    pet_id: 10,
    recurso_id: 1,
    status: "agendado",
    ...extras,
  };
}

function slot(horario, extras = {}) {
  return montarSlotsModal({
    capacidade: { janela_inicio: "08:00", janela_fim: "18:00" },
    dataRef: DIA,
    duracaoMinutos: 60,
    recursos: [BANHEIRA],
    ...extras,
  }).find((item) => item.horario === horario);
}

test("servico de 75 minutos so aparece livre quando termina ate as 18h", () => {
  assert.equal(slot("16:30", { duracaoMinutos: 75 }).livre, true);
  for (const horario of ["17:00", "17:30"]) {
    const resultado = slot(horario, { duracaoMinutos: 75 });
    assert.equal(resultado.livre, false);
    assert.equal(resultado.foraExpediente, true);
    assert.equal(resultado.sugestao, null);
  }
  assert.equal(slot("17:00").livre, true);
});

test("conflito no trecho final do servico impede falso livre de 30 minutos", () => {
  const agendamentos = [reserva("10:00", "10:30")];
  assert.equal(slot("09:00", { agendamentos, duracaoMinutos: 75 }).livre, false);
  assert.equal(slot("09:00", { agendamentos, duracaoMinutos: 60 }).livre, true);
});

test("capacidade usa pico simultaneo e aceita fronteiras adjacentes", () => {
  const recursos = [{ ...BANHEIRA, capacidade_simultanea: 2 }];
  const agendamentos = [reserva("09:00", "10:00"), reserva("10:00", "11:00")];
  const resultado = slot("09:30", { recursos, agendamentos });
  assert.equal(resultado.livre, true);
  assert.equal(resultado.sugestao.ocupacao_no_slot, 1);
  assert.equal(resultado.sugestao.vagas_disponiveis, 1);
  agendamentos.push(reserva("09:45", "10:15"));
  assert.equal(slot("09:30", { recursos, agendamentos }).livre, false);
});

test("cancelados e encerrados nao ocupam capacidade", () => {
  const agendamentos = ["cancelado", "entregue", "no_show"].map((status) =>
    reserva("09:00", "11:00", { status }),
  );
  assert.equal(slot("09:30", { agendamentos }).livre, true);
  agendamentos.push(reserva("09:00", "11:00", { status: "em_banho" }));
  assert.equal(slot("09:30", { agendamentos }).livre, false);
});

test("recurso selecionado cheio nao fica livre pela sugestao de outro recurso", () => {
  const extras = {
    recursos: [BANHEIRA, { ...BANHEIRA, id: 2, nome: "Banheira 2" }],
    agendamentos: [reserva("09:00", "11:00")],
    sugestoes: [{ horario_inicio: `${DIA}T09:30:00`, recurso_id: 2 }],
  };
  assert.equal(slot("09:30", { ...extras, form: { recurso_id: "1" } }).livre, false);
  const resultado = slot("09:30", extras);
  assert.equal(resultado.livre, true);
  assert.equal(resultado.sugestao.recurso_id, 2);
});

test("fallback de sugestoes truncadas preserva recurso e duracao completa", () => {
  const resultado = slot("16:00", { duracaoMinutos: 75, sugestoes: [] });
  assert.equal(resultado.livre, true);
  assert.equal(resultado.sugestao.recurso_id, 1);
  assert.equal(resultado.sugestao.horario_inicio, `${DIA}T16:00:00`);
  assert.equal(resultado.sugestao.horario_fim, `${DIA}T17:15:00`);
});

test("recursos inativos e IDs fora do catalogo da loja nao sao sugeridos", () => {
  const resultado = slot("09:30", {
    recursos: [BANHEIRA, { ...BANHEIRA, id: 2, ativo: false }],
    agendamentos: [reserva("09:00", "11:00", { recurso_id: 999 })],
  });
  assert.equal(resultado.livre, true);
  assert.equal(resultado.sugestao.recurso_id, 1);
  assert.equal(slot("09:30", { form: { recurso_id: 999 } }).livre, false);
  assert.equal(slot("09:30", { recursos: [{ ...BANHEIRA, ativo: false }] }).livre, false);
  assert.equal(
    slot("09:30", {
      recursos: [{ ...BANHEIRA, ativo: false }],
      form: { recurso_id: 1 },
    }).livre,
    false,
  );
});

test("intervalo iniciado na vespera ocupa abertura sem deslocar horario de parede", () => {
  const agendamentos = [
    reserva("23:00", "09:00", { data_hora_inicio: "2030-10-19T23:00:00-03:00" }),
  ];
  assert.equal(slot("08:00", { agendamentos }).livre, false);
  assert.equal(slot("09:00", { agendamentos }).livre, true);
});

test("intervalos anonimos da capacidade cobrem vespera ausente da lista diaria", () => {
  const capacidade = {
    data: DIA,
    janela_inicio: "08:00",
    janela_fim: "18:00",
    recursos: [
      {
        recurso_id: 1,
        intervalos_ocupados: [
          {
            data_hora_inicio: `${DIA}T00:00:00`,
            data_hora_fim_prevista: `${DIA}T09:00:00`,
          },
        ],
      },
    ],
  };
  assert.equal(slot("08:00", { capacidade, agendamentos: [] }).livre, false);
  assert.equal(slot("09:00", { capacidade, agendamentos: [] }).livre, true);
});

test("ocupacao da capacidade substitui lista sem duplicar reservas e ignora outro dia", () => {
  const agendamentos = [reserva("09:00", "11:00")];
  const capacidade = {
    data: DIA,
    recursos: [{ recurso_id: 1, intervalos_ocupados: agendamentos }],
  };
  const recursos = [{ ...BANHEIRA, capacidade_simultanea: 2 }];
  const resultado = slot("09:30", { agendamentos, capacidade, recursos });
  assert.equal(resultado.livre, true);
  assert.equal(resultado.sugestao.ocupacao_no_slot, 1);
  assert.equal(
    slot("09:30", {
      capacidade: { ...capacidade, data: "2030-10-19" },
      agendamentos: [],
    }).livre,
    true,
  );
});

test("pet ocupado em outro recurso tambem nao recebe sugestao livre", () => {
  const agendamentos = [reserva("09:00", "11:00", { recurso_id: 2, pet_id: 3 })];
  assert.equal(slot("09:30", { agendamentos, form: { recurso_id: 1, pet_id: 3 } }).livre, false);
  assert.equal(slot("09:30", { agendamentos, form: { recurso_id: 1, pet_id: 4 } }).livre, true);
});

test("sugestao antiga nao altera data ou duracao do fallback atual", () => {
  for (const sugestao of [
    { horario_inicio: "2030-10-19T09:00:00", horario_fim: "2030-10-19T10:15:00" },
    { horario_inicio: `${DIA}T09:00:00`, horario_fim: `${DIA}T09:30:00` },
  ]) {
    const resultado = slot("09:00", {
      duracaoMinutos: 75,
      sugestoes: [{ ...sugestao, recurso_id: 1 }],
    });
    assert.equal(resultado.sugestao.horario_inicio, `${DIA}T09:00:00`);
    assert.equal(resultado.sugestao.horario_fim, `${DIA}T10:15:00`);
  }
});
