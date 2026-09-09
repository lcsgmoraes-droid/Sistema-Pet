import assert from "node:assert/strict";
import { test } from "node:test";
import { calcularDevolucaoParceiro } from "./devolucaoParceiroUtils.js";

const registro = {
  saldo_aberto: 172.66,
  itens_devolucao: [
    {
      produto_id: 1,
      produto_nome: "Cimalgex",
      quantidade: 8,
      quantidade_devolvida: 0,
      quantidade_disponivel: 8,
      valor_total: 109.21,
      valor_devolvido: 0,
    },
    {
      produto_id: 2,
      produto_nome: "Doxifin",
      quantidade: 3,
      quantidade_devolvida: 0,
      quantidade_disponivel: 3,
      valor_total: 63.45,
      valor_devolvido: 0,
    },
  ],
};

test("devolve somente a quantidade selecionada e calcula baixa proporcional", () => {
  assert.deepEqual(calcularDevolucaoParceiro(registro, { 1: "2", 2: "" }), {
    itens: [{ produto_id: 1, quantidade: 2, valor_total: 27.3 }],
    total: 27.3,
    erro: null,
  });
});

test("devolucoes sucessivas preservam o centavo e fecham o total original", () => {
  const seguinte = structuredClone(registro);
  seguinte.saldo_aberto = 145.36;
  Object.assign(seguinte.itens_devolucao[0], {
    quantidade_devolvida: 2,
    quantidade_disponivel: 6,
    valor_devolvido: 27.3,
  });
  assert.equal(calcularDevolucaoParceiro(seguinte, { 1: 2, 2: 1 }).total, 48.46);
  assert.equal(calcularDevolucaoParceiro(seguinte, { 1: 6, 2: 3 }).total, 145.36);
});

test("valida excesso, negativos, fracao invalida, produto estranho e saldo", () => {
  for (const quantidades of [{ 1: 9 }, { 1: -1 }, { 1: 0.0001 }, { 1: "invalido" }, { 999: 2 }]) {
    assert.ok(calcularDevolucaoParceiro(registro, quantidades).erro);
  }
  assert.match(
    calcularDevolucaoParceiro({ ...registro, saldo_aberto: 10 }, { 1: 2 }).erro,
    /saldo/,
  );
});

test("quantidades fracionadas aceitam virgula e campos vazios nao selecionam produtos", () => {
  assert.equal(calcularDevolucaoParceiro(registro, { 1: "0,5" }).total, 6.83);
  assert.deepEqual(calcularDevolucaoParceiro(registro, {}).itens, []);
});
