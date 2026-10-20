import assert from "node:assert/strict";
import { test } from "node:test";
import { atalhoDiretoCorePet, carregarNotaDiretaCorePet } from "./notaDiretaCorePet.mjs";

test("atalho local aceita somente venda positiva com abertura explícita", () => {
  assert.equal(atalhoDiretoCorePet("10501", true), true);
  for (const id of ["", "0", "-1", "123abc", "../123"])
    assert.equal(atalhoDiretoCorePet(id, true), false);
  assert.equal(atalhoDiretoCorePet("10501", false), false);
});

test("carrega nota exata por venda fora de qualquer página sem consultar outra lista ou Bling", async () => {
  const calls = [];
  const api = {
    async get(path) {
      calls.push(path);
      return {
        data: {
          id: 10501,
          provedor: "intnfe",
          numero: null,
          status: "processando",
          totais: { valor_total: 1234.5 },
        },
      };
    },
  };
  const nota = await carregarNotaDiretaCorePet(api, "10501");
  assert.deepEqual(calls, ["/nfe/vendas/10501/detalhes"]);
  assert.equal(nota.venda_id, 10501);
  assert.equal(nota.valor, 1234.5);
});

test("não substitui nota por número coincidente, outro provedor ou erro403/404", async () => {
  for (const data of [
    { id: 2, provedor: "intnfe" },
    { id: 10501, provedor: "bling" },
  ]) {
    await assert.rejects(
      carregarNotaDiretaCorePet({ get: async () => ({ data }) }, "10501"),
      /não correspondem/,
    );
  }
  for (const status of [403, 404]) {
    const error = Object.assign(new Error("Sem acesso à nota"), { response: { status } });
    await assert.rejects(
      carregarNotaDiretaCorePet(
        {
          get: async () => {
            throw error;
          },
        },
        "10501",
      ),
      (caught) => caught === error,
    );
  }
});
