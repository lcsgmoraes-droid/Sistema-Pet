import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calcularItemEtiquetaBalanca,
  compararPrecosEtiquetaBalanca,
  lerEtiquetaBalanca,
} from "./pdvEtiquetaBalanca.js";
import { montarItensVendaPayload } from "./pdvVendaPayload.js";
import { produtoCorrespondeCodigoBalanca } from "./pdvProdutoBuscaUtils.js";

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

test("etiquetas corrigidas usam seis digitos de produto e cinco de valor", () => {
  for (const [codigo, sku, totalCentavos] of [
    ["2000151001435", "0151", 143],
    ["2000152001434", "0152", 143],
    ["2000153001433", "0153", 143],
    ["2000154000718", "0154", 71],
  ]) {
    const etiqueta = lerEtiquetaBalanca(codigo);
    assert.equal(etiqueta.codigoProdutoSemZeros, sku.slice(1));
    assert.equal(etiqueta.totalCentavos, totalCentavos);
    assert.equal(produtoCorrespondeCodigoBalanca({ codigo: sku }, etiqueta.codigoProduto), true);
  }

  // A etiqueta antiga do 0150 foi gerada com cadastro errado na balanca.
  const etiqueta15 = lerEtiquetaBalanca("2000015001144");
  assert.equal(etiqueta15.codigoProdutoSemZeros, "15");
  assert.equal(produtoCorrespondeCodigoBalanca({ codigo: "15" }, etiqueta15.codigoProduto), true);
  assert.equal(
    produtoCorrespondeCodigoBalanca({ codigo: "0150" }, etiqueta15.codigoProduto),
    false,
  );
});

test("rejeita erro de leitura, valor zerado e formato comum", () => {
  assert.match(lerEtiquetaBalanca("2002024015557").erro, /inválido/);
  assert.match(lerEtiquetaBalanca("2002024000002").erro, /valor/);
  assert.equal(lerEtiquetaBalanca("7891234567895"), null);
});

test("compara preco da etiqueta e do sistema com o mesmo peso", () => {
  const etiqueta = lerEtiquetaBalanca("2002024008961");
  assert.deepEqual(
    compararPrecosEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 24.77 }, 28.9),
    {
      codigo: "2002024008961",
      quantidade: 0.31,
      precoKgEtiqueta: 28.9,
      precoKgSistema: 24.77,
      totalEtiqueta: 8.96,
      totalSistema: 7.68,
      pesoInformado: false,
    },
  );
  assert.match(compararPrecosEtiquetaBalanca(etiqueta, produtoGranel, 24.77).erro, /não fecha/);
  assert.match(
    compararPrecosEtiquetaBalanca(etiqueta, produtoGranel, 28.9, "0,311").erro,
    /não fecham/,
  );
});

test("nao inventa peso quando preco por kg mudou ou ha mais de um peso possivel", () => {
  const etiqueta = lerEtiquetaBalanca("2002024015556");
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 28.88 }).erro,
    /não fecha/,
  );
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 5 }).erro,
    /mais de um peso/,
  );
  assert.match(
    calcularItemEtiquetaBalanca(etiqueta, { ...produtoGranel, preco_venda: 0 }).erro,
    /preço por kg/,
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

test("pede peso impresso quando o total aceita mais de um peso", () => {
  const etiqueta = lerEtiquetaBalanca("2002024015556");
  const resultado = compararPrecosEtiquetaBalanca(etiqueta, produtoGranel, 5, "3,110");
  assert.equal(resultado.quantidade, 3.11);
  assert.equal(resultado.totalEtiqueta, 15.55);
  assert.equal(resultado.totalSistema, 89.88);
});

test("a venda preserva o preço por kg escolhido e o total correspondente", () => {
  const comparacao = compararPrecosEtiquetaBalanca(
    lerEtiquetaBalanca("2002024008961"),
    { ...produtoGranel, preco_venda: 24.77 },
    28.9,
  );
  for (const [preco, total] of [
    [comparacao.precoKgEtiqueta, comparacao.totalEtiqueta],
    [comparacao.precoKgSistema, comparacao.totalSistema],
  ]) {
    const [item] = montarItensVendaPayload({
      itens: [
        {
          tipo: "produto",
          produto_id: 2024,
          quantidade: comparacao.quantidade,
          preco_unitario: preco,
          subtotal: total,
        },
      ],
    });
    assert.equal(item.quantidade, 0.31);
    assert.equal(item.preco_unitario, preco);
    assert.equal(item.subtotal, total);
  }
});
