import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { criarPayloadEnderecoAdicional } from "./pdvEndereco.js";
import { resolveCepMunicipio } from "../utils/cepMunicipio.js";

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

function criarRenderHook(arquivo, nome, dependencias) {
  const estados = [];
  let indice = 0;
  const useState = (inicial) => {
    const posicao = indice++;
    if (!(posicao in estados)) estados[posicao] = inicial;
    return [
      estados[posicao],
      (valor) => {
        estados[posicao] = typeof valor === "function" ? valor(estados[posicao]) : valor;
      },
    ];
  };
  const source = readFileSync(new URL(arquivo, import.meta.url), "utf8")
    .replace(/^import[^\r\n]+\r?\n/gm, "")
    .replace(/^export /gm, "");
  const deps = { useState, alert: () => {}, ...dependencias };
  const hook = new Function(...Object.keys(deps), `${source}\nreturn ${nome};`)(
    ...Object.values(deps),
  );
  return (props) => {
    indice = 0;
    return hook(props);
  };
}

const consultarCepTeste = (cep) =>
  resolveCepMunicipio(cep, {
    fetchImpl: async (url) => {
      assert.equal(url, "https://viacep.com.br/ws/16900600/json/");
      return {
        ok: true,
        json: async () => ({
          logradouro: "Rua de Teste",
          bairro: "Centro",
          localidade: "Andradina",
          uf: "SP",
          ibge: "3502101",
        }),
      };
    },
  });

test("cadastro consulta CEP e corrige IBGE no adicional existente, preservando seus dados", async () => {
  const render = criarRenderHook("./useClientesNovoEnderecos.js", "useClientesNovoEnderecos", {
    confirmarCorePet: async () => true,
    resolveCepMunicipio: consultarCepTeste,
  });
  render().abrirModalEndereco();
  assert.equal(render().enderecoAtual.codigo_municipio, "");

  const legado = {
    tipo: "entrega",
    apelido: "Trabalho",
    cep: "16900-600",
    endereco: "Rua de Teste",
    numero: "15",
    complemento: "Sala 2",
    bairro: "Centro",
    cidade: "Andradina",
    estado: "SP",
  };
  render().setEnderecosAdicionais([legado]);
  render().abrirModalEndereco(0);
  await render().buscarCepModal(legado.cep);
  assert.equal(render().enderecoAtual.codigo_municipio, "3502101");
  render().salvarEndereco();
  assert.deepEqual(render().enderecosAdicionais, [{ ...legado, codigo_municipio: "3502101" }]);
  assert.equal(legado.codigo_municipio, undefined);

  render().abrirModalEndereco(0);
  render().setEnderecoAtual({ ...render().enderecoAtual, codigo_municipio: "3502101" });
  render().salvarEndereco();
  assert.equal(render().enderecosAdicionais[0].codigo_municipio, "3502101");
});

test("PDV salva IBGE próprio do adicional sem herdar o código do endereço principal", async () => {
  const enderecoExistente = {
    tipo: "entrega",
    endereco: "Rua Existente",
    codigo_municipio: "4106902",
  };
  const cliente = {
    id: 123,
    codigo_municipio: "4106902",
    enderecos_adicionais: [enderecoExistente],
  };
  const chamadas = [];
  let clienteSalvo;
  const props = {
    vendaAtual: { cliente },
    setVendaAtual: (atualizar) => atualizar({ cliente }),
  };
  const render = criarRenderHook("./usePDVEndereco.js", "usePDVEndereco", {
    api: {
      async put(url, payload) {
        chamadas.push({ url, payload });
        clienteSalvo = { ...cliente, ...payload };
      },
    },
    buscarClientePorId: async () => clienteSalvo || cliente,
    criarPayloadEnderecoAdicional,
    resolveCepMunicipio: consultarCepTeste,
  });
  render(props).abrirModalEndereco();
  assert.equal(render(props).enderecoAtual.codigo_municipio, "");
  render(props).setEnderecoAtual({
    ...render(props).enderecoAtual,
    cep: "16900600",
    numero: "15",
    complemento: "Casa 2",
    apelido: "Casa",
  });
  await render(props).buscarCepModal("16900600");
  await render(props).salvarEnderecoNoCliente();

  assert.equal(chamadas.length, 1);
  assert.equal(chamadas[0].url, "/clientes/123");
  assert.deepEqual(Object.keys(chamadas[0].payload), ["enderecos_adicionais"]);
  assert.deepEqual(chamadas[0].payload.enderecos_adicionais, [
    enderecoExistente,
    {
      tipo: "entrega",
      apelido: "Casa",
      cep: "16900600",
      endereco: "Rua de Teste",
      numero: "15",
      complemento: "Casa 2",
      bairro: "Centro",
      cidade: "Andradina",
      estado: "SP",
      codigo_municipio: "3502101",
    },
  ]);
  assert.equal(cliente.codigo_municipio, "4106902");
  assert.deepEqual(cliente.enderecos_adicionais, [enderecoExistente]);
});

for (const [arquivo, nome] of [
  ["./useClientesNovoEnderecos.js", "useClientesNovoEnderecos"],
  ["./usePDVEndereco.js", "usePDVEndereco"],
]) {
  test(`${nome} ignora resposta de CEP anterior após o usuário alterar o endereço`, async () => {
    let responder;
    const render = criarRenderHook(arquivo, nome, {
      api: {},
      buscarClientePorId: () => {},
      criarPayloadEnderecoAdicional,
      confirmarCorePet: async () => true,
      resolveCepMunicipio: () => new Promise((resolve) => (responder = resolve)),
    });
    const props = { vendaAtual: {}, setVendaAtual: () => {} };
    render(props).abrirModalEndereco();
    render(props).setEnderecoAtual({ ...render(props).enderecoAtual, cep: "16900-600" });
    const busca = render(props).buscarCepModal("16900-600");
    render(props).setEnderecoAtual({
      ...render(props).enderecoAtual,
      cep: "80000-000",
      cidade: "Curitiba",
      estado: "PR",
      codigo_municipio: "",
    });
    responder(await consultarCepTeste("16900-600"));
    await busca;
    assert.equal(render(props).enderecoAtual.cep, "80000-000");
    assert.equal(render(props).enderecoAtual.cidade, "Curitiba");
    assert.equal(render(props).enderecoAtual.codigo_municipio, "");
  });
}
