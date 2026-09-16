import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularTotalBase,
  nomeArquivoPdf,
  preencherItemComProduto,
  sortearEmpresas,
} from "./orcamentosGrupoUtils.js";

test("calcula o total do orçamento principal", () => {
  assert.equal(
    calcularTotalBase([
      { quantidade: 2, preco_unitario_base: 10 },
      { quantidade: 1.5, preco_unitario_base: 20 },
    ]),
    50,
  );
});

test("produto do estoque preenche descrição, unidade e preço de venda do PDV", () => {
  const item = preencherItemComProduto(
    { quantidade: 2, unidade: "un", preco_unitario_base: 0 },
    {
      id: 42,
      nome: "Ração Teste",
      unidade: "KG",
      preco_venda: 100,
      preco_venda_pdv: 89.9,
    },
  );

  assert.deepEqual(item, {
    produto_id: 42,
    descricao: "Ração Teste",
    quantidade: 2,
    unidade: "KG",
    preco_unitario_base: 89.9,
  });
});

test("sorteio preserva empresas fixadas e não repete seleção", () => {
  const resultado = sortearEmpresas({
    empresas: [{ id: 1 }, { id: 2 }, { id: 3 }],
    selecoes: [
      { empresa_id: 2, fixada: true },
      { empresa_id: 1, fixada: false },
    ],
    quantidade: 2,
    random: () => 0,
  });

  assert.equal(resultado[0].empresa_id, 2);
  assert.equal(resultado[0].fixada, true);
  assert.equal(new Set(resultado.map((item) => item.empresa_id)).size, 2);
});

test("nomeia PDF individual e conjunto", () => {
  assert.equal(nomeArquivoPdf({ numero: "ORC-1" }, 5), "ORC-1-cotacao-5.pdf");
  assert.equal(nomeArquivoPdf({ numero: "ORC-1" }), "ORC-1-todos.pdf");
});
