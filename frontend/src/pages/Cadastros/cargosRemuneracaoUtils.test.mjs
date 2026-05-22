import assert from "node:assert/strict";
import test from "node:test";
import {
  calcularPercentualPorValor,
  calcularValorPorPercentual,
  sincronizarCampoRemuneracao,
} from "./cargosRemuneracaoUtils.js";

test("calcula valor a partir do percentual e salario base", () => {
  assert.equal(calcularValorPorPercentual("2098", "8"), "167.84");
  assert.equal(calcularValorPorPercentual("2098", "7,84"), "164.48");
});

test("calcula percentual a partir do valor e salario base", () => {
  assert.equal(calcularPercentualPorValor("2098", "167.84"), "8.00");
  assert.equal(calcularPercentualPorValor("2098", "164,48"), "7.84");
});

test("sincroniza percentual e valor dos encargos do cargo", () => {
  const form = {
    salario_base: "2098",
    inss_patronal_percentual: "20",
    inss_patronal_valor: "0",
    fgts_percentual: "8",
    fgts_valor: "0",
    inss_funcionario_percentual: "0",
    inss_funcionario_valor: "0",
  };

  assert.equal(sincronizarCampoRemuneracao(form, "fgts_percentual", "8").fgts_valor, "167.84");
  assert.equal(sincronizarCampoRemuneracao(form, "fgts_valor", "167.84").fgts_percentual, "8.00");
  assert.equal(
    sincronizarCampoRemuneracao(form, "inss_funcionario_percentual", "7.84").inss_funcionario_valor,
    "164.48",
  );
  assert.equal(
    sincronizarCampoRemuneracao(form, "inss_funcionario_valor", "164.48").inss_funcionario_percentual,
    "7.84",
  );
});
