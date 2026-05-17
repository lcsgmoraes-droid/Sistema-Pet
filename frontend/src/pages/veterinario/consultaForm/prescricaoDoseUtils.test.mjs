import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularDosePrescricaoPorPeso,
  obterPesoParaCalculoDose,
} from "./prescricaoDoseUtils.js";

test("obterPesoParaCalculoDose usa peso informado na consulta antes do cadastro do pet", () => {
  assert.equal(
    obterPesoParaCalculoDose({ peso_kg: "12,5" }, { peso: "8" }),
    12.5,
  );
});

test("obterPesoParaCalculoDose usa peso do cadastro do pet quando a consulta ainda não informou peso", () => {
  assert.equal(
    obterPesoParaCalculoDose({ peso_kg: "" }, { peso: "8,2" }),
    8.2,
  );
});

test("calcularDosePrescricaoPorPeso calcula dose média usando campos do catálogo", () => {
  const dose = calcularDosePrescricaoPorPeso(
    {
      dose_min_mgkg: 10,
      dose_max_mgkg: 20,
    },
    5,
  );

  assert.deepEqual(dose, {
    dose_mg: "75.00",
    unidade: "mg",
  });
});
