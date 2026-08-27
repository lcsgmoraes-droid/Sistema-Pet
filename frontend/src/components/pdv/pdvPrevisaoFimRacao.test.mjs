import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularDataFimPorPrazo,
  formatarDataFimRacao,
  resumirPrevisaoFimRacao,
  validarDataFimRacao,
} from "./pdvPrevisaoFimRacao.js";

const referencia = new Date(2026, 7, 27, 10, 0, 0);

test("calcula a data local a partir do prazo sem desvio de fuso", () => {
  assert.equal(calcularDataFimPorPrazo(30, referencia), "2026-09-26");
  assert.equal(formatarDataFimRacao("2026-09-26"), "26/09/2026");
});

test("aceita apenas data futura e prazo entre 1 e 365 dias", () => {
  assert.equal(validarDataFimRacao("2026-08-28", referencia), true);
  assert.equal(validarDataFimRacao("2026-08-27", referencia), false);
  assert.equal(calcularDataFimPorPrazo(0, referencia), "");
  assert.equal(calcularDataFimPorPrazo(366, referencia), "");
});

test("resume a escolha registrada no item do carrinho", () => {
  assert.equal(
    resumirPrevisaoFimRacao({ racao_data_prevista_fim: "2026-09-10" }),
    "Acaba em 10/09/2026",
  );
  assert.equal(
    resumirPrevisaoFimRacao({ racao_prazo_estimado_dias: 30 }),
    "Acaba em cerca de 30 dias",
  );
  assert.equal(resumirPrevisaoFimRacao({}), "Avisar quando acabar");
});
