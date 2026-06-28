import assert from "node:assert/strict";
import { test } from "node:test";
import {
  criarEstadoChecksInicial,
  executarIntroducaoChecks,
  toCount,
} from "./introducaoGuiadaChecks.js";

test("toCount normaliza formatos comuns de resposta", () => {
  assert.equal(toCount([1, 2]), 2);
  assert.equal(toCount({ items: [1] }), 1);
  assert.equal(toCount({ data: [1, 2, 3] }), 3);
  assert.equal(toCount({ total: 4 }), 4);
  assert.equal(toCount({ count: 5 }), 5);
  assert.equal(toCount(null), 0);
});

test("criarEstadoChecksInicial preserva todas as chaves conhecidas como false", () => {
  const checks = criarEstadoChecksInicial();
  assert.equal(checks.empresaFiscal, false);
  assert.equal(checks.formasPagamento, false);
  assert.equal(checks.categoriasFinanceiras, false);
  assert.equal(checks.entradaXml, false);
  assert.equal(checks.whatsappConfig, false);
});

test("executarIntroducaoChecks marca checks com respostas positivas e ignora falhas", async () => {
  const respostas = new Map([
    ["/empresa/fiscal", { regime_tributario: "simples" }],
    [
      "/empresa/dados-cadastrais",
      {
        cnpj: "00.000.000/0001-00",
        razao_social: "Pet Teste",
        endereco: "Rua A",
        numero: "1",
        bairro: "Centro",
        cidade: "Presidente Prudente",
        uf: "SP",
      },
    ],
    ["/contas-bancarias?apenas_ativas=true", [{ id: 1 }]],
    ["/financeiro/formas-pagamento?apenas_ativas=true", [{ id: 2 }]],
    ["/financeiro/categorias", { total: 2 }],
    ["/dre/categorias", [{ id: 1 }]],
    ["/dre/subcategorias", [{ id: 10 }]],
    ["/vendas?page=1&per_page=1", { total: 1 }],
  ]);

  const api = {
    async get(url) {
      if (url === "/compras/entrada-xml?limit=1") {
        throw new Error("Modulo sem acesso");
      }
      return { data: respostas.get(url) ?? {} };
    },
  };

  const checks = await executarIntroducaoChecks(api);

  assert.equal(checks.empresaFiscal, true);
  assert.equal(checks.empresaDados, true);
  assert.equal(checks.contasBancarias, true);
  assert.equal(checks.formasPagamento, true);
  assert.equal(checks.categoriasFinanceiras, true);
  assert.equal(checks.dreBase, true);
  assert.equal(checks.temVendas, true);
  assert.equal(checks.entradaXml, false);
});
