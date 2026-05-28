import assert from "node:assert/strict";
import test from "node:test";

import {
  avaliarAptidaoRacao,
  combinarProdutosComAptidao,
  escolherRacaoAptaPorTexto,
  extrairListaProdutos,
  normalizarTexto,
  pontuarBuscaRacao,
  prepararProdutosComAptidao,
} from "./calculadoraRacaoUtils.js";

const racaoCompleta = (overrides = {}) => ({
  id: 1,
  nome: "Special Dog Carne Adulto 15kg",
  codigo: "SD-CARNE-15",
  eh_racao: true,
  peso_embalagem: 15,
  preco_venda: 199.9,
  classificacao_racao: "premium",
  porte_animal: "medio",
  fase_publico: "adulto",
  sabor_proteina: "carne",
  especies_indicadas: "caes",
  tabela_consumo: '{"adulto":[{"peso":10,"gramas":180}]}',
  ...overrides,
});

test("normaliza textos para busca sem acentos e caixa", () => {
  assert.equal(normalizarTexto("  Ração CÃES Premium  "), "racao caes premium");
});

test("extrai lista de produtos de formatos comuns da API", () => {
  assert.deepEqual(extrairListaProdutos([{ id: 1 }]), [{ id: 1 }]);
  assert.deepEqual(extrairListaProdutos({ items: [{ id: 2 }] }), [{ id: 2 }]);
  assert.deepEqual(extrairListaProdutos('{"produtos":[{"id":3}]}'), [{ id: 3 }]);
  assert.deepEqual(extrairListaProdutos("json invalido"), []);
});

test("avalia aptidao de racao completa e incompleta", () => {
  assert.equal(avaliarAptidaoRacao(racaoCompleta()).apta, true);

  const incompleta = avaliarAptidaoRacao(
    racaoCompleta({
      peso_embalagem: null,
      tabela_consumo: null,
    }),
  );

  assert.equal(incompleta.apta, false);
  assert.equal(incompleta.faltantes.includes("peso da embalagem"), true);
  assert.equal(incompleta.faltantes.includes("tabela de consumo"), true);
});

test("prepara e combina produtos com aptidao sem duplicar ids", () => {
  const preparados = prepararProdutosComAptidao([
    racaoCompleta({ id: 1 }),
    { id: 2, nome: "Brinquedo", preco_venda: 10 },
  ]);

  assert.equal(preparados.length, 1);
  assert.equal(preparados[0].aptidao.apta, true);

  const combinados = combinarProdutosComAptidao(
    preparados,
    [racaoCompleta({ id: 1, nome: "Special Dog Atualizada" })],
  );

  assert.equal(combinados.length, 1);
  assert.equal(combinados[0].nome, "Special Dog Atualizada");
});

test("busca considera todos os termos antes de escolher uma racao", () => {
  const racao = racaoCompleta({ id: 10 });
  const produtoComCodigoParecido = racaoCompleta({
    id: 20,
    nome: "Produto Codigo 15",
    codigo: "15",
  });

  assert.equal(pontuarBuscaRacao(produtoComCodigoParecido, "special dog carne 15"), 0);

  const escolhida = escolherRacaoAptaPorTexto(
    "special dog carne 15",
    [produtoComCodigoParecido, racao],
  );

  assert.equal(escolhida.id, 10);
});
