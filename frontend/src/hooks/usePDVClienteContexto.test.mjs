import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../scripts/helpers/reactControllerHarness.mjs";

function adiar() {
  let resolve;
  const promise = new Promise((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

test("resposta lenta do cliente anterior não sobrescreve pendências do atual", async () => {
  const primeiro = adiar();
  const segundo = adiar();
  const h = createControllerHarness(
    fileURLToPath(new URL("./usePDVClienteContexto.js", import.meta.url)),
    {
      exportName: "usePDVClienteContexto",
      mocks: new Map([
        [
          "../api",
          {
            __esModule: true,
            default: { get: (url) => (url.includes("/1/") ? primeiro.promise : segundo.promise) },
          },
        ],
        ["../contexts/ModulosContext", { useModulos: () => ({ moduloAtivo: () => false }) }],
      ]),
      props: { vendaAtual: { cliente: { id: 1 } }, setVendaAtual() {} },
    },
  );
  await h.settle();
  await h.update({ vendaAtual: { cliente: { id: 2 } } });
  segundo.resolve({ data: { resumo: { total_vendas: 1, total_geral_em_aberto: 20 } } });
  await h.settle();
  primeiro.resolve({ data: { resumo: { total_vendas: 9, total_geral_em_aberto: 900 } } });
  await h.settle();
  assert.equal(h.tree.vendasEmAbertoInfo.total_geral_em_aberto, 20);
  h.unmount();
});

test("limpar cliente invalida consulta pendente sem reaparecer o saldo antigo", async () => {
  const consulta = adiar();
  const h = createControllerHarness(
    fileURLToPath(new URL("./usePDVClienteContexto.js", import.meta.url)),
    {
      exportName: "usePDVClienteContexto",
      mocks: new Map([
        ["../api", { __esModule: true, default: { get: () => consulta.promise } }],
        ["../contexts/ModulosContext", { useModulos: () => ({ moduloAtivo: () => false }) }],
      ]),
      props: { vendaAtual: { cliente: { id: 1 } }, setVendaAtual() {} },
    },
  );
  await h.settle();
  await h.act(() => h.tree.limparClienteSelecionado());
  await h.update({ vendaAtual: { cliente: null } });
  consulta.resolve({ data: { resumo: { total_vendas: 9, total_geral_em_aberto: 900 } } });
  await h.settle();
  assert.equal(h.tree.vendasEmAbertoInfo, null);
  h.unmount();
});
