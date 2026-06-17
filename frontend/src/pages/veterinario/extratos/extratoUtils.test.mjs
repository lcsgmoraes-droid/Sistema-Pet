import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExtratoDownloadName,
  buildExtratoParams,
  normalizarColunasSelecionadas,
  resumirLinhasExtrato,
} from "./extratoUtils.js";

test("normalizarColunasSelecionadas remove duplicadas e ignora invalidas", () => {
  assert.deepEqual(normalizarColunasSelecionadas(["nome", "nome", "preco_total", "x"]), [
    "nome",
    "preco_total",
  ]);
});

test("buildExtratoParams envia ids e colunas selecionadas", () => {
  assert.deepEqual(
    buildExtratoParams({ consultaId: 12, internacaoId: 8 }, ["nome", "preco_total"]),
    { consulta_id: 12, internacao_id: 8, colunas: "nome,preco_total" },
  );
});

test("resumirLinhasExtrato separa contabilizadas e detalhes", () => {
  const resumo = resumirLinhasExtrato([
    { contabilizar_total: true },
    { contabilizar_total: false },
    { contabilizar_total: true },
  ]);

  assert.deepEqual(resumo, { contabilizadas: 2, detalhes: 1 });
});

test("buildExtratoDownloadName usa contexto preferencial", () => {
  assert.equal(
    buildExtratoDownloadName({ consultaId: 55 }, "pdf"),
    "extrato_veterinario_consulta_55.pdf",
  );
  assert.equal(
    buildExtratoDownloadName({ internacaoId: 9 }, "xlsx"),
    "extrato_veterinario_internacao_9.xlsx",
  );
});
