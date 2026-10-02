import assert from "node:assert/strict";
import test from "node:test";

import { obterContextoRevisaoCaixa } from "./caixaRevisao.js";

test("PDV normal não envia revisão", () => {
  globalThis.window = { location: { pathname: "/pdv", search: "?guia=venda" } };
  assert.equal(obterContextoRevisaoCaixa(), null);
});

test("PDV de revisão encaminha caixa, ocorrência e motivo", () => {
  globalThis.window = {
    location: {
      pathname: "/pdv",
      search: "?caixa_revisao_id=12&data_ocorrencia=2026-10-01T15%3A30&motivo_revisao=Pagamento+esquecido",
    },
  };
  assert.deepEqual(obterContextoRevisaoCaixa(), {
    caixa_revisao_id: 12,
    data_ocorrencia: "2026-10-01T15:30",
    motivo_revisao: "Pagamento esquecido",
  });
});

test("revisão incompleta não volta silenciosamente ao caixa atual", () => {
  globalThis.window = { location: { pathname: "/pdv", search: "?caixa_revisao_id=12" } };
  assert.throws(obterContextoRevisaoCaixa, /Revisão incompleta/);
});
