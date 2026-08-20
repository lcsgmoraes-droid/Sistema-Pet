import assert from "node:assert/strict";
import test from "node:test";

import { concluirVendaComCupom } from "./pdvCupomFinalizacao.js";

test("flag ativa imprime o cupom antes de sair da venda", () => {
  const chamadas = [];

  concluirVendaComCupom({
    imprimirCupom: true,
    imprimir: () => chamadas.push("imprimir"),
    onConcluir: () => chamadas.push("sair"),
  });

  assert.deepEqual(chamadas, ["imprimir", "sair"]);
});

test("flag desmarcada sai da venda sem imprimir", () => {
  const chamadas = [];

  concluirVendaComCupom({
    imprimirCupom: false,
    imprimir: () => chamadas.push("imprimir"),
    onConcluir: () => chamadas.push("sair"),
  });

  assert.deepEqual(chamadas, ["sair"]);
});
