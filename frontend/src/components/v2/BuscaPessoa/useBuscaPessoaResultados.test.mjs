import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../../scripts/helpers/reactControllerHarness.mjs";

function preparar(props = {}) {
  const timers = new Map();
  const chamadas = [];
  let numero = 0;
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useBuscaPessoaResultados.js", import.meta.url)),
    {
      props: { value: "Ana", enabled: true, ...props },
      mocks: new Map([
        [
          "../../../api/clientes",
          {
            buscarClientes: (params, options) =>
              new Promise((resolve, reject) => chamadas.push({ params, options, resolve, reject })),
          },
        ],
      ]),
      globals: {
        AbortController,
        setTimeout: (fn) => {
          const id = ++numero;
          timers.set(id, fn);
          return id;
        },
        clearTimeout: (id) => timers.delete(id),
      },
    },
  );
  const disparar = () => {
    const [id, fn] = timers.entries().next().value;
    timers.delete(id);
    fn();
  };
  return { harness, chamadas, timers, disparar };
}

test("modo controlled não dispara busca extra e limpar cancela o debounce", async () => {
  const { harness, chamadas, timers } = preparar({ enabled: false });
  await harness.settle();
  assert.equal(timers.size, 0);
  await harness.update({ enabled: true });
  assert.equal(timers.size, 1);
  await harness.update({ value: "" });
  assert.equal(timers.size, 0);
  assert.equal(chamadas.length, 0);
  assert.deepEqual(harness.tree.suggestions, []);
  assert.equal(harness.tree.loading, false);
});

test("busca antiga não substitui resultados de um código mais recente", async () => {
  const { harness, chamadas, disparar } = preparar();
  await harness.settle();
  disparar();
  await harness.update({ value: "42" });
  assert.equal(chamadas[0].options.signal.aborted, true);
  disparar();
  chamadas[1].resolve([
    { id: 900, codigo: "142", nome: "Primeiro" },
    { id: 901, codigo: "42", nome: "Exato" },
  ]);
  await harness.settle();
  assert.deepEqual(
    harness.tree.suggestions.map((p) => p.codigo),
    ["42", "142"],
  );
  chamadas[0].resolve([{ id: 902, codigo: "9", nome: "Ana antiga" }]);
  await harness.settle();
  assert.deepEqual(
    harness.tree.suggestions.map((p) => p.codigo),
    ["42", "142"],
  );
  assert.equal(harness.tree.loading, false);
});

test("falha da consulta exibe erro e desmontagem não publica resultados tardios", async () => {
  const { harness, chamadas, disparar } = preparar();
  await harness.settle();
  disparar();
  chamadas[0].reject(new Error("Falha de rede"));
  await harness.settle();
  assert.match(harness.tree.error, /Não foi possível/);
  await harness.update({ value: "Bia" });
  disparar();
  harness.unmount();
  assert.equal(chamadas[1].options.signal.aborted, true);
  chamadas[1].resolve([{ id: 3, nome: "Bia" }]);
  await harness.settle();
  assert.deepEqual(harness.tree.suggestions, []);
});
