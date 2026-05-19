import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ajustarVendaImposto,
  dataKeyLocal,
  getStatusVendaMeta,
  montarFeriadosPadrao,
  normalizarFormaPagamentoLabel,
  parseDataLocal,
  vendaEstaEmAberto,
} from "./vendasFinanceiroUtils.js";

test("parseDataLocal preserva o dia local de strings ISO e yyyy-mm-dd", () => {
  assert.equal(dataKeyLocal("2026-05-19"), "2026-05-19");
  assert.equal(dataKeyLocal("2026-05-19T23:14:22-03:00"), "2026-05-19");
  assert.equal(parseDataLocal("invalida"), null);
});

test("normaliza formas de pagamento consolidadas", () => {
  assert.equal(normalizarFormaPagamentoLabel("pix"), "Pix");
  assert.equal(normalizarFormaPagamentoLabel("cartao_credito"), "Cartao Credito");
  assert.equal(normalizarFormaPagamentoLabel("5"), "Cartao Credito");
  assert.equal(normalizarFormaPagamentoLabel(""), "Nao informado");
});

test("identifica status de venda para filtros e badges", () => {
  assert.equal(vendaEstaEmAberto({ status: "baixa_parcial" }), true);
  assert.equal(vendaEstaEmAberto({ status: "finalizada" }), false);
  assert.deepEqual(getStatusVendaMeta("pago_nf"), { label: "Pago NF", intent: "success" });
  assert.deepEqual(getStatusVendaMeta("cancelada"), { label: "Cancelada", intent: "danger" });
});

test("monta feriados padrao com datas fixas e moveis", () => {
  const feriados = montarFeriadosPadrao([2026]);

  assert.equal(feriados["2026-01-01"], "Confraternização Universal");
  assert.equal(feriados["2026-02-16"], "Carnaval");
  assert.equal(feriados["2026-04-03"], "Sexta-feira Santa");
  assert.equal(feriados["2026-06-04"], "Corpus Christi");
});

test("ajustarVendaImposto remove imposto de venda sem nota e preserva venda fiscal", () => {
  const vendaSemNota = ajustarVendaImposto(
    {
      status: "finalizada",
      venda_bruta: 100,
      venda_liquida: 82,
      custo_produtos: 50,
      lucro: 32,
      imposto: 18,
      itens: [{ venda_bruta: 100, valor_liquido: 82, custo_total: 50, lucro: 32, imposto: 18 }],
    },
    false,
  );

  assert.equal(vendaSemNota.imposto_aplicado, false);
  assert.equal(vendaSemNota.imposto_original, 18);
  assert.equal(vendaSemNota.imposto, 0);
  assert.equal(vendaSemNota.venda_liquida, 100);
  assert.equal(vendaSemNota.lucro, 50);
  assert.equal(vendaSemNota.margem_sobre_venda, 50);
  assert.equal(vendaSemNota.itens[0].valor_liquido, 100);

  const vendaComNota = ajustarVendaImposto({ status: "pago_nf", imposto: 18 }, false);
  assert.equal(vendaComNota.imposto_aplicado, true);
  assert.equal(vendaComNota.imposto_original, 18);
});
