import assert from "node:assert/strict";
import test from "node:test";

import { montarComparativoManualRacoes, racaoPodeCompararPreco } from "./racaoComparadorManual.js";

test("identifica a racao mais vantajosa comparando duas opcoes manuais", () => {
  const comparativo = montarComparativoManualRacoes(
    {
      id: 829,
      nome: "Racao Birbo Premium Adultos Carne 15kg",
      peso_embalagem: 15,
      preco_venda: 99.9,
    },
    {
      id: 830,
      nome: "Racao Birbo Premium Adultos Carne 25kg",
      peso_embalagem: 25,
      preco_venda: 179.9,
    },
  );

  assert.equal(comparativo.pronto, true);
  assert.equal(comparativo.melhor.nome, "Racao Birbo Premium Adultos Carne 15kg");
  assert.equal(comparativo.pior.nome, "Racao Birbo Premium Adultos Carne 25kg");
  assert.equal(comparativo.diferencaPorKg, 0.54);
  assert.equal(comparativo.diferencaPorKgFormatada, "+R$ 0,54/kg");
  assert.equal(comparativo.itens[0].melhorOpcao, true);
  assert.equal(comparativo.itens[1].diferencaMelhorFormatada, "+R$ 0,54/kg");
});

test("nao libera comparacao quando uma das racoes nao tem peso ou preco", () => {
  const comparativo = montarComparativoManualRacoes(
    {
      id: 829,
      nome: "Racao 15kg",
      peso_embalagem: 15,
      preco_venda: 99.9,
    },
    {
      id: 831,
      nome: "Racao sem preco",
      peso_embalagem: 10,
      preco_venda: 0,
    },
  );

  assert.equal(racaoPodeCompararPreco({ peso_embalagem: 10, preco_venda: 0 }), false);
  assert.equal(comparativo.pronto, false);
  assert.equal(comparativo.itens.length, 1);
  assert.match(comparativo.motivo, /duas racoes/i);
});
