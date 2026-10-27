import assert from "node:assert/strict";
import test from "node:test";

import { buscarTransacoesParaPdf, preencherPdfComprasCliente } from "./clienteFinanceiroPdf.js";

test("o PDF busca todas as páginas com os filtros, sem depender da página exibida", async () => {
  const requisicoes = [];
  const api = {
    async get(url) {
      const parsed = new URL(url, "https://corepet.test");
      requisicoes.push(parsed);
      const pagina = Number(parsed.searchParams.get("page"));
      return {
        data: {
          historico: [{ id: pagina }],
          paginacao: { total_paginas: 3 },
        },
      };
    },
  };

  const transacoes = await buscarTransacoesParaPdf(api, 9681, {
    page: 2,
    per_page: 20,
    data_inicio: "2026-01-01",
    data_fim: "2026-09-29",
    tipo: "venda",
    status: "aberta",
  });

  assert.deepEqual(transacoes, [{ id: 1 }, { id: 2 }, { id: 3 }]);
  assert.deepEqual(
    requisicoes.map((url) => url.searchParams.get("page")),
    ["1", "2", "3"],
  );
  for (const url of requisicoes) {
    assert.equal(url.pathname, "/financeiro/cliente/9681");
    assert.equal(url.searchParams.get("per_page"), "100");
    assert.equal(url.searchParams.get("data_inicio"), "2026-01-01");
    assert.equal(url.searchParams.get("data_fim"), "2026-09-29");
    assert.equal(url.searchParams.get("tipo"), "venda");
    assert.equal(url.searchParams.get("status"), "aberta");
  }
});

function documentoPdf() {
  const textos = [];
  let paginas = 1;
  return {
    textos,
    internal: { getNumberOfPages: () => paginas },
    setFont() {},
    setFontSize() {},
    setTextColor() {},
    setDrawColor() {},
    line() {},
    setPage() {},
    splitTextToSize(texto) {
      return String(texto)
        .split("\n")
        .flatMap((linha) => linha.match(/.{1,80}/g) || [""]);
    },
    text(texto, _x, y) {
      textos.push({ texto, y });
    },
    addPage() {
      paginas += 1;
    },
    save(nome) {
      this.nome = nome;
    },
  };
}

test("PDF usa estado financeiro, referências simples, dd-mm-aaaa e observação integral entre páginas", () => {
  const documento = documentoPdf();
  const observacao =
    "Observação original do lote.\n" + "Detalhe preservado. ".repeat(800) + "FIM DA OBSERVAÇÃO";
  preencherPdfComprasCliente(documento, {
    cliente: { id: 47644, nome: "Pessoa QA", codigo: "1848" },
    filtros: {},
    geradoEm: new Date("2026-10-27T01:30:00Z"),
    transacoes: [
      {
        tipo: "venda",
        status: "finalizada",
        status_pagamento: "em_aberto",
        data: "2026-10-26",
        valor: 209.9,
        detalhes: { numero_venda: "IMP-20260915-112020" },
      },
      {
        tipo: "recebimento",
        status: "efetivado",
        valor: 209.9,
        data: "2026-10-26T00:00:00",
        detalhes: {
          recebimento_id: 12595,
          conta_receber_id: 11119,
          venda_id: 1340080,
          data_baixa: "2026-10-26",
          registrado_em: "2026-10-27T01:30:00Z",
          observacoes: observacao,
        },
      },
    ],
  });
  const texto = documento.textos.map((item) => item.texto).join("");
  assert.match(texto, /26-10-2026/);
  assert.match(texto, /Status: Em aberto/);
  assert.match(texto, /Status: Recebido/);
  assert.match(texto, /Recebimento: #12595/);
  assert.match(texto, /Conta a receber: #11119/);
  assert.match(texto, /FIM DA OBSERVAÇÃO/);
  assert.doesNotMatch(texto, /Registrado em|1340080|R\$ 12\.595|Finalizada|efetivado/);
  assert.ok(documento.internal.getNumberOfPages() > 1);
  assert.ok(
    documento.textos
      .filter((item) => !String(item.texto).startsWith("Página"))
      .every((item) => item.y <= 278),
  );
  assert.equal(documento.nome, "corepet-compras-1848-26-10-2026.pdf");
});

test("PDF não declara finalizada paga nem usa venda_id técnico como número público", () => {
  const documento = documentoPdf();
  preencherPdfComprasCliente(documento, {
    cliente: { nome: "QA" },
    filtros: {},
    transacoes: [
      {
        tipo: "venda",
        status: "finalizada",
        data: "2026-10-26",
        valor: 100,
        detalhes: { venda_id: 1340080 },
      },
    ],
  });
  const texto = documento.textos.map((item) => item.texto).join(" ");
  assert.match(texto, /Pagamento não informado/);
  assert.doesNotMatch(texto, /1340080|Finalizada \(paga\)/);
});
