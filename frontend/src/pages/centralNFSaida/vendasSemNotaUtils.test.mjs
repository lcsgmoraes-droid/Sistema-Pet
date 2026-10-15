import assert from "node:assert/strict";
import { test } from "node:test";

import {
  selecionarPaginaCompativel,
  vendaCompativelNfeNfce,
  vendasSelecionadasParaEmissao,
} from "./vendasSemNotaUtils.js";

const vendas = [
  { id: 1, compativel_nfe_nfce: true },
  { id: 2, compativel_nfe_nfce: false, tipo: "servico" },
  { id: 3, compativel_nfe_nfce: false, tipo: "mista" },
  { id: 4, compativel_nfe_nfce: false, tipo: "taxa_entrega_como_servico" },
  { id: 5, compativel_nfe_nfce: true },
];

test("selecionar pagina mantem servicos visiveis e seleciona somente vendas compativeis", () => {
  assert.deepEqual([...selecionarPaginaCompativel(vendas, new Set())], [1, 5]);
  assert.equal(vendas.length, 5);
  assert.deepEqual([...selecionarPaginaCompativel(vendas, new Set([1, 5]))], []);
});

test("um id de servico em selecao antiga nunca entra no lote de emissao", () => {
  const lote = vendasSelecionadasParaEmissao(vendas, new Set([1, 2, 3, 4, 5]));
  assert.deepEqual(
    lote.map((venda) => venda.id),
    [1, 5],
  );
});

test("pagina so com servicos ou sem diagnostico de composicao nao pode emitir", () => {
  const bloqueadas = [...vendas.filter((venda) => !vendaCompativelNfeNfce(venda)), { id: 6 }];
  assert.deepEqual([...selecionarPaginaCompativel(bloqueadas, new Set())], []);
  assert.deepEqual(vendasSelecionadasParaEmissao(bloqueadas, new Set([2, 3, 4, 6])), []);
});
