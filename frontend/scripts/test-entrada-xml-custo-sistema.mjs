import assert from "node:assert/strict";

import {
  calcularMargemPorPrecoVenda,
  calcularPrecoVendaPorMargem,
  obterBaseMargemEntrada,
} from "../src/components/entrada-xml/entradaXmlUtils.js";

const baseManual = obterBaseMargemEntrada({ custoNF: 10, custoSistema: 12.5 });
assert.equal(baseManual.value, "sistema");
assert.equal(baseManual.valor, 12.5);
assert.equal(baseManual.fallback, false);
assert.equal(calcularPrecoVendaPorMargem(baseManual.valor, 50), 25);
assert.equal(calcularMargemPorPrecoVenda(25, baseManual.valor), 50);

const baseSemCustoManual = obterBaseMargemEntrada({ custoNF: 10, custoSistema: 0 });
assert.equal(baseSemCustoManual.value, "nf");
assert.equal(baseSemCustoManual.valor, 10);
assert.equal(baseSemCustoManual.fallback, true);

const baseInvalida = obterBaseMargemEntrada({ custoNF: 8.75, custoSistema: "invalido" });
assert.equal(baseInvalida.valor, 8.75);
assert.equal(baseInvalida.fallback, true);

console.log("Entrada XML custo do sistema: OK");
