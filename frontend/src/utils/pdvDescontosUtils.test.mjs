import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calcularCuponsVenda,
  converterDescontosLegados,
  normalizarDescontosVenda,
  recalcularVendaComDescontos,
  resumirDescontosVenda,
} from "./pdvDescontosUtils.js";
import { montarPayloadVenda } from "./pdvVendaPayload.js";
import { recalcularItemComPrecoEDesconto } from "./pdvDescontoItensUtils.js";
import { recalcularSubtotalItem } from "./pdvCarrinhoItensUtils.js";

const itens = [
  {
    produto_id: 1,
    tipo: "produto",
    preco_unitario: 100,
    quantidade: 1,
    desconto_valor: 10,
    subtotal: 90,
  },
  {
    produto_id: 2,
    tipo: "produto",
    preco_unitario: 100,
    quantidade: 1,
    desconto_valor: 0,
    subtotal: 100,
  },
];
const venda = {
  itens,
  desconto_venda_valor: 5,
  cupom_code: "PROMO15",
  cupom_discount_applied: 15,
  tem_entrega: true,
  entrega: { taxa_entrega_total: 10 },
};

test("manual do produto fica nesse item enquanto global/cupom ficam separados", () => {
  const atualizada = recalcularVendaComDescontos(venda);
  assert.deepEqual(
    atualizada.itens.map((item) => item.desconto_valor),
    [10, 0],
  );
  assert.equal(atualizada.subtotal, 190);
  assert.equal(atualizada.total, 180);
  assert.equal(atualizada.desconto_valor, 30);
  assert.deepEqual(resumirDescontosVenda(atualizada), {
    itens: 10,
    global: 5,
    cupom: 15,
    manual: 15,
    total: 30,
  });
  const payload = montarPayloadVenda(atualizada);
  assert.deepEqual(
    payload.itens.map((item) => item.desconto_item),
    [10, 0],
  );
  assert.equal(payload.desconto_venda_valor, 5);
  assert.equal(payload.cupom_discount_applied, 15);
  assert.equal(payload.desconto_valor, 30);
});

test("retirar cupom preserva descontos manuais de item e venda", () => {
  const atualizada = recalcularVendaComDescontos(venda, itens, {
    cupom_code: null,
    cupom_discount_applied: null,
  });
  assert.equal(atualizada.total, 195);
  assert.equal(atualizada.itens[0].desconto_valor, 10);
  assert.equal(atualizada.desconto_venda_valor, 5);
});

test("retirar desconto global preserva cupom e desconto do produto", () => {
  const atualizada = recalcularVendaComDescontos(venda, itens, { desconto_venda_valor: 0 });
  assert.equal(atualizada.total, 185);
  assert.equal(atualizada.cupom_discount_applied, 15);
  assert.equal(atualizada.itens[0].desconto_valor, 10);
});

test("editar quantidade de item vindo da API preserva seu desconto exclusivo", () => {
  const alterado = recalcularSubtotalItem(
    { ...itens[0], desconto_valor: undefined, desconto_item: 10 },
    2,
  );
  const atualizada = recalcularVendaComDescontos(venda, [alterado, itens[1]]);
  assert.equal(atualizada.total, 280);
  assert.equal(atualizada.itens[0].desconto_valor, 10);
  assert.equal(atualizada.itens[1].desconto_valor, 0);
});

test("novo contrato sem desconto global envia zero explicitamente", () => {
  const atualizada = recalcularVendaComDescontos({ itens, desconto_venda_valor: 0 });
  const payload = montarPayloadVenda(atualizada);
  assert.equal(payload.desconto_venda_valor, 0);
  assert.equal(payload.desconto_valor, 10);
});

test("legado preserva desconto e liquido por linha sem conversao na refinalizacao", () => {
  const atualizada = normalizarDescontosVenda({
    itens: [
      { ...itens[0], desconto_valor: undefined, desconto_item: 15, subtotal: 85 },
      { ...itens[1], desconto_valor: undefined, desconto_item: 5, subtotal: 95 },
    ],
    subtotal: 180,
    total: 180,
    desconto_valor: 20,
    desconto_venda_valor: null,
    cupom_code: "OLD",
    cupom_discount_applied: 10,
  });
  assert.equal(atualizada.total, 180);
  assert.equal(atualizada.desconto_origem_legado, true);
  assert.deepEqual(
    atualizada.itens.map((item) => item.desconto_valor),
    [15, 5],
  );
  assert.equal(atualizada.desconto_venda_valor, null);
  const payload = montarPayloadVenda(atualizada);
  assert.equal(payload.desconto_venda_valor, null);
  assert.deepEqual(
    payload.itens.map((item) => [item.desconto_item, item.subtotal]),
    [
      [15, 85],
      [5, 95],
    ],
  );
  assert.equal(recalcularVendaComDescontos(atualizada).total, 180);
});

test("load/payload legado conserva valores historicos sem inferir origem", () => {
  const atualizada = normalizarDescontosVenda({
    itens,
    total: 180,
    desconto_valor: 20,
    cupom_code: "OLD",
    cupom_discount_applied: 10,
  });
  assert.deepEqual(
    atualizada.itens.map((item) => item.desconto_valor),
    [10, 0],
  );
  assert.equal(atualizada.total, 180);
  assert.equal(montarPayloadVenda(atualizada).desconto_valor, 20);
});

test("legado com centavos conserva cada linha no load e payload", () => {
  const atualizada = normalizarDescontosVenda({
    itens: Array.from({ length: 7 }, () => ({
      preco_unitario: 1,
      quantidade: 1,
      desconto_item: 0.1,
      subtotal: 0.9,
    })),
    subtotal: 6.3,
    total: 6.3,
    desconto_valor: 0.7,
    cupom_code: "OLD",
    cupom_discount_applied: 0.47,
  });
  const payload = montarPayloadVenda(atualizada);
  assert.equal(payload.desconto_venda_valor, null);
  assert.equal(payload.desconto_valor, 0.7);
  assert.deepEqual(
    payload.itens.map((item) => item.subtotal),
    Array(7).fill(0.9),
  );
  assert.equal(recalcularVendaComDescontos(atualizada).total, 6.3);
});

test("cupom percentual usa base dos produtos apos manuais sem frete e acompanha alteracoes", () => {
  const cupom = { code: "P10", coupon_type: "percent", discount_percent: 10 };
  let atual = recalcularVendaComDescontos({
    itens: [{ ...itens[0], desconto_valor: 0, subtotal: 100 }],
    desconto_venda_valor: 0,
    cupom_code: "P10",
    cupons_detalhes: [cupom],
    tem_entrega: true,
    entrega: { taxa_entrega_total: 10 },
  });
  assert.equal(atual.cupom_discount_applied, 10);
  assert.equal(atual.total, 100);
  atual = recalcularVendaComDescontos(atual, [recalcularSubtotalItem(atual.itens[0], 2)]);
  assert.equal(atual.cupom_discount_applied, 20);
  assert.equal(atual.total, 190);
  atual = recalcularVendaComDescontos(
    atual,
    [{ ...atual.itens[0], desconto_valor: 20, subtotal: 180 }],
    { desconto_venda_valor: 10 },
  );
  assert.equal(atual.cupom_discount_applied, 17);
  assert.equal(atual.cupons_detalhes[0].discount_applied, 17);
  assert.equal(montarPayloadVenda(atual).cupom_discount_applied, 17);
  assert.equal(atual.total, 163);
});

test("cupons sequenciais recalculam fixo/percentual ao reduzir base sem apagar manuais", () => {
  const resultado = calcularCuponsVenda(100, [
    { code: "FIXO20", coupon_type: "fixed", discount_value: 20 },
    { code: "P10", coupon_type: "percent", discount_percent: 10 },
  ]);
  assert.deepEqual(
    resultado.detalhes.map((cupom) => cupom.discount_applied),
    [20, 8],
  );
  assert.equal(resultado.restante, 72);
  const reduzido = recalcularVendaComDescontos({
    itens: [{ ...itens[0], preco_unitario: 25, desconto_valor: 10, subtotal: 15 }],
    desconto_venda_valor: 5,
    cupom_code: "FIXO20,P10",
    cupons_detalhes: resultado.detalhes,
  });
  assert.equal(reduzido.desconto_venda_valor, 5);
  assert.equal(reduzido.itens[0].desconto_valor, 10);
  assert.equal(reduzido.cupom_discount_applied, 10);
  assert.deepEqual(
    reduzido.cupons_detalhes.map((cupom) => cupom.discount_applied),
    [10, 0],
  );
});

test("item fracionado usa quantidade real para desconto manual e arredonda antes do liquido", () => {
  const fracao = recalcularItemComPrecoEDesconto(
    { quantidade: 0.5, preco_unitario: 100 },
    { tipoDesconto: "valor", descontoValor: 10 },
  );
  assert.equal(fracao.subtotal, 40);
  const centavos = recalcularItemComPrecoEDesconto(
    { quantidade: 0.333, preco_unitario: 1 },
    { tipoDesconto: "percentual", descontoPercentual: 5 },
  );
  assert.equal(centavos.desconto_valor, 0.02);
  assert.equal(centavos.subtotal, 0.31);
  assert.equal(
    recalcularSubtotalItem({ ...centavos, tipo_desconto_aplicado: "percentual" }, 0.333).subtotal,
    0.31,
  );
});

test("converter legado exige chamada deliberada e conserva total antes do novo ajuste", () => {
  const original = {
    itens: [
      { ...itens[0], desconto_valor: undefined, desconto_item: 15, subtotal: 85 },
      { ...itens[1], desconto_valor: undefined, desconto_item: 5, subtotal: 95 },
    ],
    total: 180,
    subtotal: 180,
    desconto_valor: 20,
    desconto_venda_valor: null,
    cupom_code: "OLD",
    cupom_discount_applied: 10,
  };
  const convertida = converterDescontosLegados(original);
  assert.equal(original.desconto_venda_valor, null);
  assert.deepEqual(
    original.itens.map((item) => item.desconto_item),
    [15, 5],
  );
  assert.deepEqual(
    convertida.itens.map((item) => item.desconto_valor),
    [7.5, 2.5],
  );
  assert.equal(convertida.desconto_venda_valor, 0);
  assert.equal(convertida.desconto_origem_legado, false);
  assert.equal(convertida.total, 180);
  assert.equal(recalcularVendaComDescontos(convertida).total, 180);
  assert.equal(
    recalcularVendaComDescontos(convertida, convertida.itens, { desconto_venda_valor: 5 }).total,
    175,
  );
});

test("editar quantidade no legado mantém G nulo e não converte descontos por item", () => {
  const original = normalizarDescontosVenda({
    itens: [
      { ...itens[0], desconto_item: 15, desconto_valor: undefined, subtotal: 85 },
      { ...itens[1], desconto_item: 5, desconto_valor: undefined, subtotal: 95 },
    ],
    subtotal: 180,
    total: 180,
    desconto_valor: 20,
    cupom_code: "OLD",
    cupom_discount_applied: 10,
  });
  const alterada = recalcularVendaComDescontos(original, [
    recalcularSubtotalItem(original.itens[0], 2),
    original.itens[1],
  ]);
  assert.equal(alterada.desconto_venda_valor, null);
  assert.deepEqual(
    alterada.itens.map((item) => item.desconto_valor),
    [15, 5],
  );
  assert.equal(alterada.cupom_discount_applied, 10);
  assert.equal(alterada.total, 280);
});

test("metadata do GET mantém cupom percentual recalculável na venda reaberta", () => {
  const carregada = normalizarDescontosVenda({
    itens: [{ ...itens[0], desconto_valor: undefined, desconto_item: 0, subtotal: 100 }],
    subtotal: 100,
    total: 90,
    desconto_valor: 10,
    desconto_venda_valor: 0,
    cupom_code: "P10",
    cupom_discount_applied: 10,
    cupons_detalhes: [
      { code: "P10", coupon_type: "percent", discount_percent: 10, discount_value: null },
    ],
  });
  assert.equal(carregada.cupons_detalhes[0].discount_applied, 10);
  const alterada = recalcularVendaComDescontos(carregada, [
    recalcularSubtotalItem(carregada.itens[0], 2),
  ]);
  assert.equal(alterada.cupom_discount_applied, 20);
  assert.equal(montarPayloadVenda(alterada).cupom_discount_applied, 20);
});
