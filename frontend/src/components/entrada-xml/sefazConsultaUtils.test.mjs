import assert from "node:assert/strict";
import test from "node:test";
import { normalizarMensagemErroSefaz } from "./sefazConsultaUtils.mjs";

test("explica timeout e falha de rede sem resposta HTTP", () => {
  assert.match(normalizarMensagemErroSefaz({ code: "ECONNABORTED" }), /demorou mais/);
  assert.match(normalizarMensagemErroSefaz({ code: "ERR_NETWORK" }), /conectar ao sistema/);
});

test("preserva o detalhe do servidor e identifica excesso de consultas", () => {
  assert.match(
    normalizarMensagemErroSefaz({ response: { status: 502, data: { detail: "SEFAZ cStat 656" } } }),
    /Aguarde pelo menos 1 hora/,
  );
  assert.match(
    normalizarMensagemErroSefaz({ response: { status: 429, data: { detail: "Aguarde 1 hora" } } }),
    /Aguarde 1 hora/,
  );
  assert.match(
    normalizarMensagemErroSefaz({
      response: { status: 422, data: { detail: [{ msg: "Chave inválida" }] } },
    }),
    /Chave inválida/,
  );
});

test("distingue resposta indisponível e HTTP sem detalhe", () => {
  assert.match(
    normalizarMensagemErroSefaz({ response: { status: 502, data: { detail: "Cloudflare" } } }),
    /temporariamente indisponível/,
  );
  assert.match(normalizarMensagemErroSefaz({ response: { status: 503 } }), /HTTP 503/);
});
