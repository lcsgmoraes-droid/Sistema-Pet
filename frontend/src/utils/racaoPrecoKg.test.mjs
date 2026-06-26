import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularPrecoPorKg,
  compararRacoesPorPrecoKg,
  formatarPrecoPorKg,
  obterResumoPrecoPorKg,
} from "./racaoPrecoKg.js";

test("calcula preco por kg usando o preco efetivo do PDV quando existe", () => {
  const produto = {
    nome: "Racao Birbo Premium Adultos Carne 15kg",
    peso_embalagem: 15,
    preco_venda: 120,
    preco_venda_pdv: 99.9,
  };

  assert.equal(calcularPrecoPorKg(produto), 6.66);
  assert.equal(formatarPrecoPorKg(produto), "R$ 6,66/kg");
});

test("retorna null quando nao ha peso ou preco validos", () => {
  assert.equal(calcularPrecoPorKg({ peso_embalagem: 0, preco_venda: 99.9 }), null);
  assert.equal(calcularPrecoPorKg({ peso_embalagem: 15, preco_venda: 0 }), null);
  assert.equal(formatarPrecoPorKg({ peso_embalagem: 15, preco_venda: 0 }), "");
});

test("monta resumo com peso, preco e preco por kg formatados", () => {
  const resumo = obterResumoPrecoPorKg({
    produto_nome: "Racao 25kg",
    peso_embalagem: "25",
    preco_unitario: "179.90",
  });

  assert.deepEqual(resumo, {
    disponivel: true,
    nome: "Racao 25kg",
    pesoKg: 25,
    preco: 179.9,
    precoPorKg: 7.2,
    pesoFormatado: "25kg",
    precoFormatado: "R$ 179,90",
    precoPorKgFormatado: "R$ 7,20/kg",
  });
});

test("aceita peso_embalagem_kg vindo do resultado da calculadora", () => {
  const resumo = obterResumoPrecoPorKg({
    produto_nome: "Racao calculada",
    peso_embalagem_kg: 15,
    preco: 99.9,
  });

  assert.equal(resumo.disponivel, true);
  assert.equal(resumo.precoPorKg, 6.66);
  assert.equal(resumo.precoPorKgFormatado, "R$ 6,66/kg");
});

test("compara racoes pelo menor preco por kg e calcula diferenca contra a melhor", () => {
  const comparativo = compararRacoesPorPrecoKg([
    {
      produto_id: 829,
      produto_nome: "Racao Birbo Premium Adultos Carne 15kg",
      peso_embalagem: 15,
      preco_unitario: 99.9,
    },
    {
      produto_id: 830,
      produto_nome: "Racao Birbo Premium Adultos Carne 25kg",
      peso_embalagem: 25,
      preco_unitario: 179.9,
    },
  ]);

  assert.equal(comparativo.length, 2);
  assert.equal(comparativo[0].produtoId, 829);
  assert.equal(comparativo[0].melhorOpcao, true);
  assert.equal(comparativo[0].diferencaMelhor, 0);
  assert.equal(comparativo[1].produtoId, 830);
  assert.equal(comparativo[1].melhorOpcao, false);
  assert.equal(comparativo[1].diferencaMelhor, 0.54);
  assert.equal(comparativo[1].diferencaMelhorFormatada, "+R$ 0,54/kg");
});
