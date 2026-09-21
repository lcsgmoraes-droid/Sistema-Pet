import assert from "node:assert/strict";

import { resolveCepMunicipio } from "./cepMunicipio.js";

const viaCepOk = async (url) => {
  assert.equal(url, "https://viacep.com.br/ws/16900600/json/");
  return {
    ok: true,
    json: async () => ({
      cep: "16900-600",
      logradouro: "Avenida Rio Grande do Sul",
      bairro: "Vila Alpina",
      localidade: "Andradina",
      uf: "SP",
      ibge: "3502101",
    }),
  };
};

const endereco = await resolveCepMunicipio("16900-600", {
  cidade: "Andradina",
  estado: "SP",
  fetchImpl: viaCepOk,
});

assert.deepEqual(endereco, {
  cep: "16900600",
  endereco: "Avenida Rio Grande do Sul",
  bairro: "Vila Alpina",
  cidade: "Andradina",
  estado: "SP",
  codigo_municipio: "3502101",
});

await assert.rejects(
  resolveCepMunicipio("16900-600", {
    cidade: "Aracatuba",
    estado: "SP",
    fetchImpl: viaCepOk,
  }),
  /pertence a Andradina\/SP/,
);
