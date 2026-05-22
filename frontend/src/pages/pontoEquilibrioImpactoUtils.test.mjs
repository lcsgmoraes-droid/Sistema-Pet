import assert from "node:assert/strict";
import { test } from "node:test";
import { calcularImpactoPontoEquilibrio } from "./pontoEquilibrioImpactoUtils.js";

test("calcula aumento de ponto de equilibrio para novo custo fixo", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: 20000,
    margemContribuicaoPercentual: 50,
    faturamento: 18000,
    ticketMedio: 200,
    impactoCustoFixo: 3000,
  });

  assert.equal(resultado.calculavel, true);
  assert.equal(resultado.novoCustoFixo, 13000);
  assert.equal(resultado.impactoPontoEquilibrio, 6000);
  assert.equal(resultado.novoPontoEquilibrio, 26000);
  assert.equal(resultado.novaFaltaFaturar, 8000);
  assert.equal(resultado.vendasImpacto, 30);
});

test("calcula reducao de ponto de equilibrio quando custo fixo diminui", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: 20000,
    margemContribuicaoPercentual: 50,
    faturamento: 18000,
    ticketMedio: 200,
    impactoCustoFixo: -1000,
  });

  assert.equal(resultado.calculavel, true);
  assert.equal(resultado.novoCustoFixo, 9000);
  assert.equal(resultado.impactoPontoEquilibrio, -2000);
  assert.equal(resultado.novoPontoEquilibrio, 18000);
  assert.equal(resultado.novaFaltaFaturar, 0);
  assert.equal(resultado.vendasImpacto, -10);
});

test("marca simulacao como indefinida quando margem nao permite calcular", () => {
  const resultado = calcularImpactoPontoEquilibrio({
    despesasFixas: 10000,
    pontoEquilibrio: null,
    margemContribuicaoPercentual: 0,
    faturamento: 18000,
    ticketMedio: 200,
    impactoCustoFixo: 3000,
  });

  assert.equal(resultado.calculavel, false);
  assert.equal(resultado.novoCustoFixo, 13000);
  assert.equal(resultado.impactoPontoEquilibrio, null);
  assert.equal(resultado.novoPontoEquilibrio, null);
});
