import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ajustarVendaImposto,
  calcularValorRecebidoVenda,
  dataKeyLocal,
  filtrarVendasRelatorio,
  formatarDataVendaFinanceiro,
  getStatusVendaMeta,
  getTextoComparacaoPeriodo,
  montarFeriadosPadrao,
  normalizarFormaPagamentoLabel,
  ordenarVendasRelatorio,
  parseDataLocal,
  sanitizarNumero,
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

test("calcula valor recebido visual conforme status da venda", () => {
  assert.equal(calcularValorRecebidoVenda({ valor_recebido: 12.5, status: "aberta" }), 12.5);
  assert.equal(calcularValorRecebidoVenda({ status: "finalizada", venda_bruta: 100 }), 100);
  assert.equal(calcularValorRecebidoVenda({ status: "aberta", venda_bruta: 100 }), 0);
});

test("formata datas e sanitiza numeros para os paineis financeiros", () => {
  assert.equal(formatarDataVendaFinanceiro("2026-05-19T23:14:22-03:00"), "19/05/2026");
  assert.equal(formatarDataVendaFinanceiro("invalida"), "N/A");
  assert.equal(sanitizarNumero(null), 0);
  assert.equal(sanitizarNumero(Number.POSITIVE_INFINITY), 0);
  assert.equal(sanitizarNumero("12.5"), "12.5");
});

test("filtra e ordena vendas para relatorio personalizado", () => {
  const vendas = [
    {
      id: 1,
      data_venda: "2026-05-18",
      funcionario_nome: "Ana",
      forma_pagamento: "Pix",
      categoria: "Racao",
      status: "finalizada",
      venda_bruta: 50,
      lucro: 12,
    },
    {
      id: 2,
      data_venda: "2026-05-19",
      funcionario: "Bia",
      pagamento_principal: "Cartao Credito",
      categoria: "Medicamento",
      status: "aberta",
      venda_bruta: 100,
      lucro: 30,
    },
  ];

  assert.deepEqual(
    filtrarVendasRelatorio(vendas, {
      escopo: "filtrado",
      filtroFuncionario: "Bia",
      filtroFormaPagamento: "Cartao Credito",
      filtroCategoria: "Medicamento",
      filtroStatusLista: "em_aberto",
    }).map((venda) => venda.id),
    [2],
  );

  assert.deepEqual(ordenarVendasRelatorio(vendas, "bruta_asc").map((venda) => venda.id), [1, 2]);
  assert.deepEqual(ordenarVendasRelatorio(vendas, "lucro_desc").map((venda) => venda.id), [2, 1]);
  assert.deepEqual(ordenarVendasRelatorio(vendas, "data_desc").map((venda) => venda.id), [2, 1]);
});

test("descreve periodo de comparacao financeiro", () => {
  assert.equal(getTextoComparacaoPeriodo("periodo_anterior"), "mesmo período anterior");
  assert.equal(getTextoComparacaoPeriodo("mes_anterior"), "mesmo período do mês anterior");
  assert.equal(getTextoComparacaoPeriodo("ano_anterior"), "mesmo período do ano anterior");
  assert.equal(getTextoComparacaoPeriodo("x"), "período anterior");
});
