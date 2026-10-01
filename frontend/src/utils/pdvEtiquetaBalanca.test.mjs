import assert from "node:assert/strict";
import { test } from "node:test";
import { calcularItemEtiquetaBalanca, lerEtiquetaBalanca } from "./pdvEtiquetaBalanca.js";

const produtoGranel = {
  codigo: "2024",
  e_granel: true,
  unidade: "KG",
  preco_venda: 28.9,
};

test("as duas etiquetas identificam o mesmo produto e preservam os totais impressos", () => {
  const primeira = lerEtiquetaBalanca("2002024015556");
  const segunda = lerEtiquetaBalanca("2002024006592");

  assert.equal(primeira.codigoProdutoSemZeros, "2024");
  assert.equal(segunda.codigoProdutoSemZeros, "2024");
  assert.deepEqual(calcularItemEtiquetaBalanca(primeira, produtoGranel), {
    codigo: "2002024015556",
    quantidade: 0.538,
    precoUnitario: 28.9,
    subtotal: 15.55,
  });
  assert.equal(calcularItemEtiquetaBalanca(segunda, produtoGranel).quantidade, 0.228);
  assert.equal(calcularItemEtiquetaBalanca(segunda, produtoGranel).subtotal, 6.59);
});

test("rejeita erro de leitura, valor zerado e formato comum", () => {
  assert.match(lerEtiquetaBalanca("2002024015557").erro, /inválido/);
  assert.match(lerEtiquetaBalanca("2002024000002").erro, /valor/);
  assert.equal(lerEtiquetaBalanca("7891234567895"), null);
});

test("nao inventa peso quando preco por kg mudou ou ha mais de um peso possivel", () => {
  const etiqueta = lerEtiquetaBalanca("2002024015556");
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 28.88 }).erro,
    /peso único/,
  );
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 5 }).erro,
    /peso único/,
  );
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 0 }).erro,
    /Marque/,
  );
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, unidade: "UN" }).erro,
    /Marque/,
  );
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, e_granel: false }).erro,
    /granel/,
  );
});
