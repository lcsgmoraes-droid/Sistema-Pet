import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

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

const revisaoSource = readFileSync(
  new URL("../src/components/entrada-xml/useEntradaXmlRevisaoPrecos.js", import.meta.url),
  "utf8",
);
assert.match(revisaoSource, /atualizar_preco_venda:\s*true/);
assert.match(revisaoSource, /setAcaoProcessamento\("atualizar_preco_venda", true\)/);
assert.match(revisaoSource, /precos_venda_atualizados/);

console.log("Entrada XML custo do sistema: OK");
