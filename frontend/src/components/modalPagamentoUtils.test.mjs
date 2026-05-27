import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
  calcularResumoRecebimento,
  descreverCupomMargem,
  montarCupomParaFinalizar,
  montarPagamentoRecebido,
} from "./modalPagamentoUtils.js";

test("calcula faixas quando ha parcelas saudaveis, alerta e criticas", () => {
  const faixas = calcularFaixasParcelamento(
    {
      1: { cor: "verde" },
      2: { cor: "verde" },
      3: { cor: "amarelo" },
      4: { cor: "vermelho" },
      5: { cor: "vermelho" },
    },
    5,
  );

  assert.deepEqual(faixas, {
    saudavel: { min: 1, max: 2 },
    alerta: { min: 3, max: 3 },
    proibido: { min: 4, max: 5 },
  });
});

test("mantem tudo como proibido quando nao ha parcela verde", () => {
  const faixas = calcularFaixasParcelamento(
    {
      1: { cor: "vermelho" },
      2: { cor: "vermelho" },
    },
    2,
  );

  assert.deepEqual(faixas, {
    saudavel: { min: 1, max: 0 },
    alerta: { min: 1, max: 0 },
    proibido: { min: 1, max: 2 },
  });
});

test("ignora parcelas sem simulacao e mantem limite maximo informado", () => {
  const faixas = calcularFaixasParcelamento(
    {
      1: { cor: "verde" },
      4: { cor: "vermelho" },
    },
    4,
  );

  assert.deepEqual(faixas, {
    saudavel: { min: 1, max: 1 },
    alerta: { min: 2, max: 3 },
    proibido: { min: 4, max: 4 },
  });
});

test("calcula previa de cashback, carimbos e recompra elegiveis por canal", () => {
  const resultado = calcularBeneficiosCampanhaPreview({
    campanhasCompra: [
      {
        name: "Cashback Ouro",
        campaign_type: "cashback",
        params: {
          benefit_channels: ["loja_fisica"],
          bronze_percent: 1,
          gold_percent: 3,
          pdv_bonus_percent: 2,
        },
      },
      {
        name: "Cartao fidelidade",
        campaign_type: "loyalty_stamp",
        params: { benefit_channels: ["loja_fisica"], min_purchase_value: 20 },
      },
      {
        name: "Recompra",
        campaign_type: "quick_repurchase",
        params: {
          benefit_channels: ["loja_fisica"],
          min_purchase_value: 50,
          coupon_type: "percent",
          coupon_value: 10,
        },
      },
      {
        name: "Cashback App",
        campaign_type: "cashback",
        params: { benefit_channels: ["app"], bronze_percent: 99 },
      },
    ],
    rankCliente: "gold",
    canalVenda: "loja_fisica",
    valorBase: 100,
  });

  assert.deepEqual(resultado, {
    cashbackPrevisto: [
      {
        campanha: "Cashback Ouro",
        percentual: 5,
        valor: 5,
      },
    ],
    carimbosPrevistos: [
      {
        campanha: "Cartao fidelidade",
        quantidade: 5,
      },
    ],
    recompraPrevista: [
      {
        campanha: "Recompra",
        tipo: "percent",
        valor: 10,
      },
    ],
  });
});

test("calcula resumo do recebimento considerando pagamentos novos e existentes", () => {
  const resumo = calcularResumoRecebimento({
    valorTotal: 100,
    pagamentos: [{ valor: 20 }, { valor: 10 }],
    totalPagoExistente: 30,
    valorRecebido: 50,
  });

  assert.deepEqual(resumo, {
    valorPago: 60,
    valorRestante: 40,
    vendaQuitadaComPagamentosExistentes: false,
    podeConfirmarFinalizacao: true,
    troco: 10,
  });
});

test("monta cupom salvo na venda quando nao ha cupom aplicado na tela", () => {
  const cupom = montarCupomParaFinalizar({
    cupomAplicado: null,
    venda: {
      cupom_code: "recompra10",
      cupom_discount_applied: 12.5,
      desconto_valor: 15,
    },
  });

  assert.deepEqual(cupom, {
    code: "recompra10",
    discount_applied: 12.5,
  });
});

test("descreve cupom somente quando ha codigo e desconto", () => {
  const texto = descreverCupomMargem(
    { code: "recompra10", discount_applied: 12.5 },
    (valor) => `R$ ${valor.toFixed(2)}`,
  );

  assert.equal(
    texto,
    "A margem ficou baixa por conta do cupom RECOMPRA10 (R$ 12.50 de desconto).",
  );
  assert.equal(descreverCupomMargem(null), "");
});

test("monta pagamento de cartao com valor efetivo limitado ao restante", () => {
  const pagamento = montarPagamentoRecebido({
    formaPagamento: {
      id: 2,
      nome: "Credito",
      tipo: "cartao_credito",
      permite_parcelamento: true,
    },
    valor: 150,
    valorRestante: 100,
    bandeira: "Visa",
    nsuCartao: "123456",
    operadora: { id: 7 },
    numeroParcelas: 3,
    troco: 50,
  });

  assert.deepEqual(pagamento, {
    forma_pagamento: "Credito",
    forma_id: 2,
    forma_pagamento_id: 2,
    nome: "Credito",
    valor: 100,
    bandeira: "Visa",
    nsu_cartao: "123456",
    operadora_id: 7,
    numero_parcelas: 3,
    parcelas: 3,
    valor_recebido: 150,
    troco: null,
    is_credito_cliente: false,
    is_cashback: false,
  });
});

test("monta pagamento em dinheiro com troco e sem dados de cartao", () => {
  const pagamento = montarPagamentoRecebido({
    formaPagamento: {
      id: 1,
      nome: "Dinheiro",
      tipo: "dinheiro",
      permite_parcelamento: false,
    },
    valor: 120,
    valorRestante: 100,
    bandeira: "Visa",
    nsuCartao: "123456",
    operadora: { id: 7 },
    numeroParcelas: 2,
    troco: 20,
  });

  assert.equal(pagamento.valor, 100);
  assert.equal(pagamento.bandeira, null);
  assert.equal(pagamento.nsu_cartao, null);
  assert.equal(pagamento.numero_parcelas, 1);
  assert.equal(pagamento.troco, 20);
});
