import assert from "node:assert/strict";
import test from "node:test";
import { obterLotesValidadeDisponiveis, obterValidadeMaisProximaProduto } from "./produtosUtils.js";

const antiga = "2027-01-21";
const nova = "2027-03-10";

test("produto zerado não mostra validade antiga nem lote com saldo desatualizado", () => {
  for (const estoque_atual of [0, -1]) {
    const produto = {
      estoque_atual,
      controle_lote: false,
      validade_proxima: antiga,
      validade_proxima_listagem: antiga,
      lotes_validade_resumo: [{ data_validade: antiga, quantidade_disponivel: 1 }],
    };
    assert.equal(obterValidadeMaisProximaProduto(produto), null);
    assert.deepEqual(obterLotesValidadeDisponiveis(produto), []);
  }
});

test("resumo de lotes vazio não recupera lote histórico nem validade do cadastro", () => {
  const produto = {
    estoque_atual: 5,
    controle_lote: true,
    validade_proxima: antiga,
    lotes_validade_resumo: [],
    lotes: [{ data_validade: antiga, quantidade_disponivel: 2 }],
  };
  assert.deepEqual(obterLotesValidadeDisponiveis(produto), []);
  assert.equal(obterValidadeMaisProximaProduto(produto), null);
});

test("a validade acompanha o lote com saldo quando o lote mais antigo zera", () => {
  const produto = {
    estoque_atual: 3,
    controle_lote: true,
    validade_proxima: antiga,
    lotes_validade_resumo: [
      { data_validade: antiga, quantidade_disponivel: 0 },
      { data_validade: nova, quantidade_disponivel: 3 },
    ],
  };
  assert.equal(obterValidadeMaisProximaProduto(produto), nova);
});

test("unidades reservadas continuam tendo validade enquanto existem fisicamente", () => {
  const produto = {
    estoque_atual: 3,
    estoque_reservado: 3,
    estoque_disponivel: 0,
    controle_lote: true,
    lotes_validade_resumo: [{ data_validade: nova, quantidade_disponivel: 3 }],
  };
  assert.equal(obterValidadeMaisProximaProduto(produto), nova);
});

test("kit virtual considera seu estoque calculado", () => {
  const produto = {
    tipo_produto: "KIT",
    tipo_kit: "VIRTUAL",
    estoque_atual: 0,
    estoque_virtual: 3,
    controle_lote: false,
    validade_proxima: nova,
  };
  assert.equal(obterValidadeMaisProximaProduto(produto), nova);
});

test("cadastro sem controle de lote preserva sua validade apenas com estoque positivo", () => {
  const produto = {
    estoque_atual: 2,
    controle_lote: false,
    validade_proxima: antiga,
    lotes_validade_resumo: [],
  };
  assert.equal(obterValidadeMaisProximaProduto(produto), antiga);
});
