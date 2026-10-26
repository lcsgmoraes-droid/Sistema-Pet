import assert from "node:assert/strict";
import test from "node:test";
import {
  DADOS_ADICIONAIS_NOTA_INICIAIS,
  validarDadosAdicionaisNota,
} from "./nfeAdditionalData.mjs";

test("venda física não exige dados de marketplace nem inventa referência", () => {
  assert.equal(validarDadosAdicionaisNota(DADOS_ADICIONAIS_NOTA_INICIAIS), "");
  assert.equal(DADOS_ADICIONAIS_NOTA_INICIAIS.numero_pedido, "");
});

test("Amazon exige pedido, CNPJ e identificação da loja", () => {
  const dados = { ...DADOS_ADICIONAIS_NOTA_INICIAIS, canal: "amazon" };
  assert.match(validarDadosAdicionaisNota(dados), /número do pedido/);
  dados.numero_pedido = "PEDIDO-QA";
  assert.match(validarDadosAdicionaisNota(dados), /CNPJ/);
  dados.intermediador_cnpj = "11.222.333/0001-81";
  assert.match(validarDadosAdicionaisNota(dados), /identificação da sua loja/);
  dados.intermediador_identificacao = "VENDEDOR-QA";
  assert.equal(validarDadosAdicionaisNota(dados), "");
  dados.intermediador_identificacao = dados.numero_pedido;
  assert.match(validarDadosAdicionaisNota(dados), /não pode ser o número do pedido/);
});
