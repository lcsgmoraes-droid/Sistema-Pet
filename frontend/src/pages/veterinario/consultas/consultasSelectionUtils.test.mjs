import assert from "node:assert/strict";
import test from "node:test";

import {
  removerConsultasSelecionadas,
  toggleConsultaSelecionada,
  toggleTodasConsultasSelecionadas,
} from "./consultasUtils.js";

test("toggleConsultaSelecionada marca e desmarca uma consulta", () => {
  const marcada = toggleConsultaSelecionada([], 19);

  assert.deepEqual(marcada, [19]);
  assert.deepEqual(toggleConsultaSelecionada(marcada, 19), []);
});

test("toggleTodasConsultasSelecionadas seleciona todas as visiveis e limpa quando todas ja estao marcadas", () => {
  const consultas = [{ id: 16 }, { id: 17 }, { id: 18 }];

  const selecionadas = toggleTodasConsultasSelecionadas([], consultas);
  assert.deepEqual(selecionadas, [16, 17, 18]);
  assert.deepEqual(toggleTodasConsultasSelecionadas(selecionadas, consultas), []);
});

test("removerConsultasSelecionadas remove apenas as consultas apagadas", () => {
  const consultas = [{ id: 16 }, { id: 17 }, { id: 18 }];

  assert.deepEqual(removerConsultasSelecionadas(consultas, [16, 18]), [{ id: 17 }]);
});
