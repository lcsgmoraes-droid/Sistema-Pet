import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCalculadoraDoseFormParaPrescricao,
  calcularDosePrescricaoPorPeso,
  obterPesoParaCalculoDose,
} from "./prescricaoDoseUtils.js";

test("obterPesoParaCalculoDose usa peso informado na consulta antes do cadastro do pet", () => {
  assert.equal(obterPesoParaCalculoDose({ peso_kg: "12,5" }, { peso: "8" }), 12.5);
});

test("obterPesoParaCalculoDose usa peso do cadastro do pet quando a consulta ainda não informou peso", () => {
  assert.equal(obterPesoParaCalculoDose({ peso_kg: "" }, { peso: "8,2" }), 8.2);
});

test("calcularDosePrescricaoPorPeso exige a dose escolhida pelo veterinario", () => {
  assert.equal(calcularDosePrescricaoPorPeso({ dose_min_mgkg: 10, dose_max_mgkg: 20 }, 5), null);

  const dose = calcularDosePrescricaoPorPeso(
    {
      dose_min_mgkg: 10,
      dose_max_mgkg: 20,
    },
    5,
    15,
  );

  assert.deepEqual(dose, {
    dose_mg: "75.00",
    unidade: "mg",
  });
});

test("buildCalculadoraDoseFormParaPrescricao não escolhe o meio da faixa automaticamente", () => {
  const formCalculadora = buildCalculadoraDoseFormParaPrescricao({
    calculadoraFormAtual: {
      medicamento_id: "",
      peso_kg: "",
      dose_mg_kg: "",
      frequencia_horas: "12",
      dias: "7",
    },
    formConsulta: { peso_kg: "15" },
    itemPrescricao: {
      medicamento_id: 42,
      dose_minima_mg_kg: 20,
      dose_maxima_mg_kg: 30,
      duracao_dias: "5",
    },
    petSelecionado: { peso: "9" },
  });

  assert.deepEqual(formCalculadora, {
    medicamento_id: "42",
    peso_kg: "15",
    dose_mg_kg: "",
    frequencia_horas: "12",
    dias: "5",
  });
});
