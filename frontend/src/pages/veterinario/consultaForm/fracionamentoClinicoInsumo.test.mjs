import assert from "node:assert/strict";
import test from "node:test";

import {
  ERRO_SEM_ORIGEM_FRACIONAMENTO,
  garantirSaldoClinicoParaInsumo,
} from "./fracionamentoClinicoInsumo.js";

test("nao converte quando o estoque clinico ja atende o consumo", async () => {
  let converteu = false;
  const resultado = await garantirSaldoClinicoParaInsumo({
    api: {
      obterSugestaoFracionamentoClinico: async () => ({
        data: { necessita_fracionamento: false },
      }),
      converterFracionamentoClinico: async () => {
        converteu = true;
      },
    },
    confirmar: async () => true,
    produto: { id: 11 },
    quantidade: 3,
  });

  assert.equal(converteu, false);
  assert.equal(resultado.conversao, null);
});

test("confirma e abre a embalagem vinculada antes do consumo", async () => {
  let payload;
  const api = {
    obterSugestaoFracionamentoClinico: async () => ({
      data: {
        necessita_fracionamento: true,
        estoque_atual: 0,
        sugestao: {
          produto_origem: { id: 10, nome: "Dipirona 20 ml", unidade: "UN" },
          produto_destino: { id: 11, nome: "Dipirona clinica", unidade: "ML" },
          quantidade_origem: 1,
          fator_conversao: 20,
          quantidade_destino: 20,
          validade_apos_abertura_dias: 28,
        },
      },
    }),
    converterFracionamentoClinico: async (data) => {
      payload = data;
      return { data: { id: 99 } };
    },
  };

  const resultado = await garantirSaldoClinicoParaInsumo({
    api,
    confirmar: async () => true,
    documento: "CONSULTA-42",
    observacao: "Abertura automatica",
    produto: { id: 11 },
    quantidade: 3,
  });

  assert.equal(payload.produto_origem_id, 10);
  assert.equal(payload.produto_destino_id, 11);
  assert.equal(payload.quantidade_origem, 1);
  assert.equal(resultado.conversao.id, 99);
});

test("explica quando nao ha embalagem vinculada com saldo", async () => {
  await assert.rejects(
    garantirSaldoClinicoParaInsumo({
      api: {
        obterSugestaoFracionamentoClinico: async () => ({
          data: { necessita_fracionamento: true, sugestao: null },
        }),
      },
      confirmar: async () => true,
      produto: { id: 11 },
      quantidade: 3,
    }),
    new RegExp(ERRO_SEM_ORIGEM_FRACIONAMENTO),
  );
});
