import assert from "node:assert/strict";
import { test } from "node:test";
import {
  erroPeriodo,
  formatarDataContabilidade,
  mensagemErroContabilidade,
  periodoMesAnterior,
} from "./xmlContabilidadeUtils.mjs";

test("mês anterior respeita Brasília durante a virada UTC e anos bissextos", () => {
  assert.deepEqual(periodoMesAnterior(new Date("2026-03-01T01:30:00Z")), {
    inicio: "2026-01-01",
    fim: "2026-01-31",
  });
  assert.deepEqual(periodoMesAnterior(new Date("2024-03-01T12:00:00Z")), {
    inicio: "2024-02-01",
    fim: "2024-02-29",
  });
  assert.deepEqual(periodoMesAnterior(new Date("2026-01-15T12:00:00Z")), {
    inicio: "2025-12-01",
    fim: "2025-12-31",
  });
});

test("período inclui o mesmo dia e rejeita data inexistente ou invertida", () => {
  assert.equal(erroPeriodo({ inicio: "2026-10-19", fim: "2026-10-19" }), "");
  assert.ok(erroPeriodo({ inicio: "2026-02-29", fim: "2026-03-01" }));
  assert.ok(erroPeriodo({ inicio: "2026-10-20", fim: "2026-10-19" }));
  assert.ok(erroPeriodo({ inicio: "2026-10-19", fim: "" }));
});

test("mês anterior sempre termina no último dia para meses de 28, 29, 30 e 31 dias", () => {
  for (const [agora, inicio, fim] of [
    ["2026-03-01T12:00:00Z", "2026-02-01", "2026-02-28"],
    ["2024-03-01T12:00:00Z", "2024-02-01", "2024-02-29"],
    ["2026-05-01T12:00:00Z", "2026-04-01", "2026-04-30"],
    ["2026-02-01T12:00:00Z", "2026-01-01", "2026-01-31"],
  ]) {
    assert.deepEqual(periodoMesAnterior(new Date(agora)), { inicio, fim });
  }
  assert.deepEqual(periodoMesAnterior(new Date("2026-05-31T12:00:00Z")), {
    inicio: "2026-04-01",
    fim: "2026-04-30",
  });
});

test("datas de período não recuam um dia e instantes são apresentados em Brasília", () => {
  assert.equal(formatarDataContabilidade("2026-10-01"), "01/10/2026");
  assert.match(formatarDataContabilidade("2026-10-20T01:30:00Z", true), /19\/10\/2026.*22:30/);
});

test("erro JSON em resposta blob do download mantém a mensagem do servidor", async () => {
  assert.equal(
    await mensagemErroContabilidade(
      { response: { data: new Blob(['{"detail":"Nenhum XML disponível no período."}']) } },
      "Erro",
    ),
    "Nenhum XML disponível no período.",
  );
  assert.equal(
    await mensagemErroContabilidade({ response: { data: new Blob(["inválido"]) } }, "Erro"),
    "Erro",
  );
});
