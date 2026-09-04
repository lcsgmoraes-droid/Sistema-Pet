import assert from "node:assert/strict";
import test from "node:test";

import {
  calcularQuantidadeDestinoFracionamento,
  montarPayloadFracionamentoClinico,
  resolverConfiguracaoVinculoFracionamento,
} from "./fracionamentoClinicoUtils.js";

test("calcula o saldo clinico a partir da quantidade de frascos", () => {
  assert.equal(calcularQuantidadeDestinoFracionamento("2", "20"), 40);
});

test("monta payload normalizado para a conversao clinica", () => {
  assert.deepEqual(
    montarPayloadFracionamentoClinico({
      produtoOrigemId: "10",
      produtoDestinoId: "11",
      quantidadeOrigem: "1",
      fatorConversao: "20,5",
      validadeAposAberturaDias: "28",
      loteOrigemId: "7",
      documento: "  consulta 15 ",
      observacao: "  aberto pela veterinaria ",
    }),
    {
      produto_origem_id: 10,
      produto_destino_id: 11,
      quantidade_origem: 1,
      fator_conversao: 20.5,
      validade_apos_abertura_dias: 28,
      lote_origem_id: 7,
      documento: "consulta 15",
      observacao: "aberto pela veterinaria",
    },
  );
});

test("recupera configuracao previamente vinculada ao insumo clinico", () => {
  const vinculo = resolverConfiguracaoVinculoFracionamento(
    [{ produto_destino_id: 11, fator_conversao: 20 }],
    "11",
  );
  assert.equal(vinculo.fator_conversao, 20);
});
