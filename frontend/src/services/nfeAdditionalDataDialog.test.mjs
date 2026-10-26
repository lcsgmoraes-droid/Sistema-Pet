import assert from "node:assert/strict";
import test from "node:test";
import {
  assinarDadosAdicionaisNota,
  resolverDadosAdicionaisNota,
  solicitarDadosAdicionaisNota,
} from "./nfeAdditionalDataDialog.js";

test("revisões em fila só liberam a venda correspondente e ignoram resolução antiga", async () => {
  const apresentados = [];
  const remover = assinarDadosAdicionaisNota((dialogo) => apresentados.push(dialogo));
  const primeira = solicitarDadosAdicionaisNota({ vendaId: 123 });
  const idPrimeira = apresentados.at(-1).id;
  const segunda = solicitarDadosAdicionaisNota({ vendaId: 456 });
  assert.equal(apresentados.at(-1).vendaId, 123);
  resolverDadosAdicionaisNota(idPrimeira, false);
  assert.equal(await primeira, false);
  assert.equal(apresentados.at(-1).vendaId, 456);
  const idSegunda = apresentados.at(-1).id;
  resolverDadosAdicionaisNota(idPrimeira, true);
  assert.equal(apresentados.at(-1).vendaId, 456);
  resolverDadosAdicionaisNota(idSegunda, true);
  assert.equal(await segunda, true);
  assert.equal(apresentados.at(-1), null);
  remover();
});
