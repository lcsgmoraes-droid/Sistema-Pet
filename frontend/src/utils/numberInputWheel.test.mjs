import assert from "node:assert/strict";
import test from "node:test";

import {
  desfocarInputNumericoAoRolar,
  instalarProtecaoRodaInputsNumericos,
} from "./numberInputWheel.js";

test("desfoca input numerico ativo antes que a roda altere o valor", () => {
  let desfocado = false;
  const input = {
    matches: (seletor) => seletor === 'input[type="number"]',
    blur: () => {
      desfocado = true;
    },
  };
  input.ownerDocument = { activeElement: input };

  assert.equal(desfocarInputNumericoAoRolar({ target: input }), true);
  assert.equal(desfocado, true);
});

test("nao interfere em outros campos nem em input numerico sem foco", () => {
  const texto = {
    matches: () => false,
    ownerDocument: { activeElement: null },
    blur: () => assert.fail("campo de texto nao deveria perder o foco"),
  };
  const numeroSemFoco = {
    matches: () => true,
    ownerDocument: { activeElement: null },
    blur: () => assert.fail("input sem foco nao deveria ser alterado"),
  };

  assert.equal(desfocarInputNumericoAoRolar({ target: texto }), false);
  assert.equal(desfocarInputNumericoAoRolar({ target: numeroSemFoco }), false);
});

test("instala e remove a protecao global com captura", () => {
  const chamadas = [];
  const documento = {
    addEventListener: (...argumentos) => chamadas.push(["add", ...argumentos]),
    removeEventListener: (...argumentos) => chamadas.push(["remove", ...argumentos]),
  };

  const remover = instalarProtecaoRodaInputsNumericos(documento);
  remover();

  assert.equal(chamadas[0][0], "add");
  assert.equal(chamadas[0][1], "wheel");
  assert.equal(chamadas[0][2], desfocarInputNumericoAoRolar);
  assert.deepEqual(chamadas[0][3], { capture: true, passive: true });
  assert.deepEqual(chamadas[1], ["remove", "wheel", desfocarInputNumericoAoRolar, true]);
});
