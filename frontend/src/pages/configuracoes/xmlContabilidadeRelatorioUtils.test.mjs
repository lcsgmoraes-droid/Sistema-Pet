import assert from "node:assert/strict";
import { test } from "node:test";
import {
  filtrarDocumentosRelatorio,
  linkNotaRelatorio,
  quantidadeRelatorio,
  valorRelatorio,
} from "./xmlContabilidadeRelatorioUtils.mjs";

test("valores desconhecidos não viram zero e valores conhecidos usam BRL", () => {
  for (const valor of [null, undefined, "", "inválido"]) {
    assert.equal(valorRelatorio(valor), "Indisponível");
    assert.equal(quantidadeRelatorio(valor), "Indisponível");
  }
  assert.equal(valorRelatorio("0.00"), "R$ 0,00");
  assert.equal(valorRelatorio("17555.25"), "R$ 17.555,25");
  assert.equal(quantidadeRelatorio(10501), "10.501");
});

test("atalho identifica a venda sem incluir ações de emissão ou cancelamento", () => {
  const link = linkNotaRelatorio({ venda_id: 10501, numero: 52, provider: "intnfe" });
  assert.equal(link, "/notas-fiscais/saida?busca=52&venda_id=10501&abrir=1");
  assert.equal(
    linkNotaRelatorio({ documento_id: "10501", provider: "bling" }),
    "/notas-fiscais/saida",
  );
});

test("filtros usam situação informada, sem confundir preparada com enviada", () => {
  const docs = [
    { numero: "1", estado: "preparada", enviada: false },
    { numero: "2", estado: "pendente", enviada: false, motivo: "Aguardando confirmação fiscal" },
    { numero: "3", estado: "preparada", enviada: true },
  ];
  assert.deepEqual(
    filtrarDocumentosRelatorio(docs, "", "enviadas").map((d) => d.numero),
    ["3"],
  );
  assert.deepEqual(
    filtrarDocumentosRelatorio(docs, "", "nao_enviadas").map((d) => d.numero),
    ["1", "2"],
  );
  assert.deepEqual(
    filtrarDocumentosRelatorio(docs, "confirmação", "pendentes").map((d) => d.numero),
    ["2"],
  );
});
