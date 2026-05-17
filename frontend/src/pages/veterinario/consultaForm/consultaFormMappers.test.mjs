import assert from "node:assert/strict";
import test from "node:test";

import {
  mapConsultaParaForm,
  mapPrescricoesParaForm,
  mapProcedimentosParaForm,
} from "./consultaFormMappers.js";

test("mapConsultaParaForm restaura prescricao e procedimentos salvos no rascunho", () => {
  const form = mapConsultaParaForm({
    pet_id: 10,
    prescricao_rascunho: [
      {
        medicamento_id: 3,
        nome: "Dipirona",
        dose_mg: "120",
        unidade: "mg",
        frequencia: "a cada 12h",
      },
    ],
    procedimentos_rascunho: [
      {
        catalogo_id: 8,
        nome: "Curativo",
        valor: "35",
      },
    ],
  });

  assert.equal(form.prescricao_itens[0].nome, "Dipirona");
  assert.equal(form.prescricao_itens[0].frequencia, "a cada 12h");
  assert.equal(form.procedimentos_realizados[0].nome, "Curativo");
});

test("mapConsultaParaForm expõe retorno agendado para a consulta em andamento", () => {
  const form = mapConsultaParaForm({
    pet_id: 10,
    retorno_agendado: {
      id: 44,
      data_hora: "2026-05-20T14:30:00",
      tipo: "retorno",
    },
  });

  assert.equal(form.retorno_agendado.id, 44);
  assert.equal(form.retorno_agendado.data_hora, "2026-05-20T14:30:00");
});

test("mapPrescricoesParaForm converte prescricao persistida para campos editaveis", () => {
  const itens = mapPrescricoesParaForm([
    {
      itens: [
        {
          medicamento_catalogo_id: 4,
          nome_medicamento: "Amoxicilina",
          concentracao: "Principio",
          quantidade: "80",
          posologia: "80 mg - a cada 12h - dar com alimento",
          via_administracao: "oral",
          duracao_dias: 7,
        },
      ],
    },
  ]);

  assert.equal(itens[0].medicamento_id, "4");
  assert.equal(itens[0].dose_mg, "80");
  assert.equal(itens[0].unidade, "mg");
  assert.equal(itens[0].frequencia, "a cada 12h");
  assert.equal(itens[0].instrucoes, "dar com alimento");
});

test("mapProcedimentosParaForm converte procedimentos persistidos", () => {
  const itens = mapProcedimentosParaForm([
    {
      catalogo_id: 5,
      nome: "Aplicacao SC",
      descricao: "Medicacao subcutanea",
      valor: 45,
      observacoes: "sem intercorrencia",
    },
  ]);

  assert.equal(itens[0].catalogo_id, "5");
  assert.equal(itens[0].valor, "45");
  assert.equal(itens[0].observacoes, "sem intercorrencia");
});
