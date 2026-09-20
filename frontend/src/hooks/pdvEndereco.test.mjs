import assert from "node:assert/strict";
import test from "node:test";

import { criarPayloadEnderecoAdicional } from "./pdvEndereco.js";

test("PDV envia somente os enderecos adicionais ao atualizar o cliente", () => {
  const clienteAtual = {
    id: 123,
    nome: "Cliente teste",
    auth_user_id: 456,
    app_access_profiles: ["cliente"],
    enderecos_adicionais: [{ tipo: "entrega", endereco: "Rua Antiga" }],
  };
  const novoEndereco = {
    tipo: "entrega",
    endereco: "Rua Nova",
    cidade: "Sao Paulo",
  };

  const payload = criarPayloadEnderecoAdicional(clienteAtual, novoEndereco);

  assert.deepEqual(Object.keys(payload), ["enderecos_adicionais"]);
  assert.deepEqual(payload.enderecos_adicionais, [
    { tipo: "entrega", endereco: "Rua Antiga" },
    novoEndereco,
  ]);
  assert.equal("auth_user_id" in payload, false);
  assert.equal("app_access_profiles" in payload, false);
});

test("PDV nao altera a lista de enderecos que veio do cadastro", () => {
  const enderecoExistente = { tipo: "residencial", endereco: "Rua Existente" };
  const clienteAtual = { enderecos_adicionais: [enderecoExistente] };
  const novoEndereco = { tipo: "entrega", endereco: "Rua Nova" };

  const payload = criarPayloadEnderecoAdicional(clienteAtual, novoEndereco);

  assert.deepEqual(clienteAtual.enderecos_adicionais, [enderecoExistente]);
  assert.notEqual(payload.enderecos_adicionais, clienteAtual.enderecos_adicionais);
  assert.notEqual(payload.enderecos_adicionais[1], novoEndereco);
});

test("PDV inicia a lista quando o cliente ainda nao possui enderecos adicionais", () => {
  const novoEndereco = { tipo: "entrega", endereco: "Primeira Rua" };

  assert.deepEqual(criarPayloadEnderecoAdicional({}, novoEndereco), {
    enderecos_adicionais: [novoEndereco],
  });
});
