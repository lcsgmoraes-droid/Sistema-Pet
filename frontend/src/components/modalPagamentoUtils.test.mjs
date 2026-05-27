import assert from "node:assert/strict";
import { test } from "node:test";
import {
  calcularBeneficiosCampanhaPreview,
  calcularFaixasParcelamento,
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
