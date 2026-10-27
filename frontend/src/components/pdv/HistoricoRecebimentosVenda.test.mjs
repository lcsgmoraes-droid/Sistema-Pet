import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function preparar(get) {
  return createControllerHarness(
    fileURLToPath(new URL("./HistoricoRecebimentosVenda.jsx", import.meta.url)),
    {
      props: { vendaId: 123 },
      mocks: new Map([
        ["../../api", { __esModule: true, default: { get } }],
        ["../v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
      ]),
    },
  );
}

const recebimento = {
  recebimento_id: 12595,
  data_baixa: "2026-10-26",
  registrado_em: "2026-10-26T11:03:52.350843",
  valor: 1209.9,
  forma_pagamento: "Pix",
  observacoes: "Cliente pagou dia 28/09\nBaixado hoje após conferência.",
  status: "recebido",
  baixa_lote_id: 13,
};

test("exibe a data local e a observação integral da baixa sem repetir o registro técnico", async () => {
  const chamadas = [];
  const harness = preparar(async (url, config) => {
    chamadas.push({ url, params: config.params });
    return { data: { recebimentos: [recebimento], paginacao: { total_pages: 1 } } };
  });
  await harness.settle();
  assert.deepEqual(chamadas, [
    { url: "/vendas/123/recebimentos-historico", params: { page: 1, per_page: 20 } },
  ]);
  const texto = elementText(harness.tree);
  assert.match(texto, /26-10-2026/);
  assert.match(texto, /R\$\s*1\.209,90/);
  assert.ok(texto.includes(recebimento.observacoes));
  assert.match(texto, /Baixa em lote #13/);
  assert.doesNotMatch(texto, /Registrado em|2026-10-26T|12595/);
});

test("pagina recebimentos e mantém estornos identificados", async () => {
  const paginas = [];
  const harness = preparar(async (_url, { params }) => {
    paginas.push(params.page);
    return {
      data: {
        recebimentos: [{ ...recebimento, status: "estornado", valor: -1209.9 }],
        paginacao: { total_pages: 2 },
      },
    };
  });
  await harness.settle();
  assert.match(elementText(harness.tree), /Estornado/);
  const proxima = elements(harness.tree).find(
    (node) => node.type === "BotaoInteracao" && elementText(node) === "Próximos recebimentos",
  );
  await harness.act(() => proxima.props.onClick());
  assert.deepEqual(paginas, [1, 2]);
  assert.match(elementText(harness.tree), /Página 2 de 2/);
});

test("falha da consulta fica visível e permite retentar sem declarar ausência de baixas", async () => {
  let chamadas = 0;
  const harness = preparar(async () => {
    chamadas++;
    if (chamadas === 1) throw new Error("timeout");
    return { data: { recebimentos: [recebimento], paginacao: {} } };
  });
  await harness.settle();
  assert.match(elementText(harness.tree), /Não foi possível carregar os recebimentos/);
  assert.doesNotMatch(elementText(harness.tree), /Não há registros/);
  const retentar = elements(harness.tree).find((node) => node.type === "BotaoInteracao");
  await harness.act(() => retentar.props.onClick());
  assert.equal(chamadas, 2);
  assert.match(elementText(harness.tree), /26-10-2026/);
});
