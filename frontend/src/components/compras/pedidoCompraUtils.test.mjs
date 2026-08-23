import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calcularQuantidadeTotalUnidadesPedido,
  formatarQuantidadeCompraPedido,
  montarTooltipQuantidadeCompraPedido,
  montarRascunhoPedidoReposicaoGrupo,
  normalizarItemPedido,
  normalizarQuantidadePorEmbalagemPedido,
} from "./pedidoCompraUtils.js";

test("formatarQuantidadeCompraPedido mostra embalagem com total em unidades", () => {
  const item = {
    quantidade_pedida: 2,
    unidade_compra: "CX",
    quantidade_por_embalagem: 12,
  };

  assert.equal(calcularQuantidadeTotalUnidadesPedido(item), 24);
  assert.equal(formatarQuantidadeCompraPedido(item), "2 CX (24 unid)");
  assert.equal(
    montarTooltipQuantidadeCompraPedido(item),
    "Cada CX contem 12 unidades vendaveis. Este item representa 24 unidades no total.",
  );
});

test("formatarQuantidadeCompraPedido preserva unitario simples", () => {
  const item = normalizarItemPedido({
    produto_id: 15,
    produto_nome: "Sache Frango",
    quantidade_pedida: 12,
    unidade_compra: "UN",
    quantidade_por_embalagem: 12,
    preco_unitario: 3.5,
  });

  assert.equal(item.unidade_compra, "UN");
  assert.equal(item.quantidade_por_embalagem, 1);
  assert.equal(item.quantidade_total_unidades, 12);
  assert.equal(formatarQuantidadeCompraPedido(item), "12 UN");
  assert.equal(montarTooltipQuantidadeCompraPedido(item), "");
});

test("formatarQuantidadeCompraPedido permite embalagem sem fator conhecido", () => {
  const item = {
    quantidade_pedida: 2,
    unidade_compra: "CX",
    quantidade_por_embalagem: "",
  };

  assert.equal(normalizarQuantidadePorEmbalagemPedido("CX", ""), null);
  assert.equal(calcularQuantidadeTotalUnidadesPedido(item), 2);
  assert.equal(formatarQuantidadeCompraPedido(item), "2 CX");
  assert.equal(
    montarTooltipQuantidadeCompraPedido(item),
    "Quantidade por CX ainda nao informada. O pedido sera enviado sem conversao para unidades.",
  );
});

test("plano do grupo vira rascunho de pedido para revisao", () => {
  const rascunho = montarRascunhoPedidoReposicaoGrupo({
    fornecedor_id: 44,
    itens: [
      {
        produto_id: 15,
        produto_nome: "Sache Frango",
        produto_codigo: "SACH-15",
        quantidade_pedida: 12,
        unidade_compra: "UN",
        quantidade_por_embalagem: 1,
        preco_unitario: 3.5,
      },
    ],
  });

  assert.equal(rascunho.fornecedor_id, "44");
  assert.match(rascunho.observacoes, /Revise fornecedor/);
  assert.deepEqual(rascunho.itens[0], {
    produto_id: 15,
    produto_nome: "Sache Frango",
    produto_codigo: "SACH-15",
    quantidade_pedida: 12,
    unidade_compra: "UN",
    quantidade_por_embalagem: 1,
    quantidade_total_unidades: 12,
    preco_unitario: 3.5,
    desconto_item: 0,
    total: 42,
  });
  assert.equal(montarRascunhoPedidoReposicaoGrupo({ fornecedor_id: 44 }), null);
});
